"""Bulk deterministic SQL generation without client-side million-row materialization."""
from pathlib import Path

import psycopg

LOCK_ID = 718029411
SIZES = {"small": 10000, "medium": 100000, "large": 1000000}


def generate(dsn: str, size: str, seed: int, schema_file: Path) -> None:
    count = SIZES[size]
    customers, products = max(1000, count // 10), max(500, count // 100)
    with psycopg.connect(dsn) as conn:
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (LOCK_ID,))
        conn.execute(schema_file.read_text())
        conn.execute("TRUNCATE commerce.order_items, commerce.payments, commerce.shipments, "
                     "commerce.inventory_movements, commerce.orders, commerce.products, "
                     "commerce.customers, commerce.suppliers, commerce.dataset_manifest")
        # MD5-derived fractions provide stable randomness independent of evaluation order.
        conn.execute("CREATE OR REPLACE FUNCTION pg_temp.r(n bigint, salt int) RETURNS double precision "
                     "LANGUAGE SQL IMMUTABLE AS $$ SELECT "
                     "(('x'||substr(md5(n::text||':'||salt::text),1,8))::bit(32)::bigint)::float8/4294967296 $$")
        conn.execute("INSERT INTO commerce.suppliers SELECT n, 'Supplier '||n, "
                     "(ARRAY['APAC','EMEA','AMER'])[1+mod(n,3)] FROM generate_series(1,50) n")
        conn.execute("INSERT INTO commerce.customers SELECT n, 'customer-'||n||'@example.invalid', "
                     "CASE WHEN n%%17=0 THEN NULL ELSE (ARRAY['APAC','EMEA','AMER'])[1+n%%3] END, "
                     "DATE '2023-01-01' + (n%%700)::int FROM generate_series(1,%s) n", (customers,))
        conn.execute("INSERT INTO commerce.products SELECT n, 1+n%%50, 'Product '||n, "
                     "'category-'||n%%12, (1+pg_temp.r(n,%s)*999)::numeric(12,2) "
                     "FROM generate_series(1,%s) n", (seed, products))
        conn.execute("INSERT INTO commerce.orders SELECT n, 1+floor(power(pg_temp.r(n,%s),3)*%s)::bigint, "
                     "TIMESTAMP '2025-01-01' + (power(pg_temp.r(n,%s),0.5)*31536000)*INTERVAL '1 second', "
                     "CASE WHEN n%%10<7 THEN 'paid' WHEN n%%10<9 THEN 'pending' ELSE 'cancelled' END, "
                     "0 FROM generate_series(1,%s) n", (seed+1, customers, seed+2, count))
        conn.execute("INSERT INTO commerce.order_items SELECT n, 1+(n-1)/3, "
                     "1+floor(power(pg_temp.r(n,%s),2.5)*%s)::bigint, 1+(n%%5)::int, "
                     "0 FROM generate_series(1,%s) n", (seed+3, products, count*3))
        conn.execute("UPDATE commerce.order_items i SET unit_price=p.price FROM commerce.products p WHERE p.id=i.product_id")
        conn.execute("UPDATE commerce.orders o SET total=x.total FROM (SELECT order_id, SUM(quantity*unit_price) AS total "
                     "FROM commerce.order_items GROUP BY order_id) x WHERE o.id=x.order_id")
        conn.execute("INSERT INTO commerce.payments SELECT id, id, total, "
                     "CASE WHEN mod(id,3)=0 THEN 'bank' ELSE 'card' END, "
                     "ordered_at+INTERVAL '1 minute' FROM commerce.orders WHERE status='paid'")
        conn.execute("INSERT INTO commerce.shipments SELECT id, id, ordered_at+INTERVAL '1 day', "
                     "CASE WHEN mod(id,13)=0 THEN NULL ELSE ordered_at+(2+mod(id,7))*INTERVAL '1 day' END, "
                     "ordered_at+INTERVAL '5 days' FROM commerce.orders WHERE status='paid'")
        conn.execute("INSERT INTO commerce.inventory_movements SELECT n, 1+(n%% %s), "
                     "CASE WHEN n%%3=0 THEN -2 ELSE 10 END, TIMESTAMP '2025-01-01' "
                     "+(n%%365)*INTERVAL '1 day' FROM generate_series(1,%s) n", (products, count))
        conn.execute("INSERT INTO commerce.dataset_manifest(singleton,seed,orders_count) VALUES (true,%s,%s)", (seed, count))
        for table in ("suppliers", "customers", "products", "orders", "order_items", "payments", "shipments", "inventory_movements"):
            conn.execute(psycopg.sql.SQL("ANALYZE commerce.{}").format(psycopg.sql.Identifier(table)))
        # Edge dataset includes duplicate foreign keys, missing relationships, NULLs and boundaries.
        conn.execute("DROP SCHEMA IF EXISTS edge_cases CASCADE; CREATE SCHEMA edge_cases AUTHORIZATION pgo_experiment")
        conn.execute("GRANT USAGE ON SCHEMA edge_cases TO pgo_reader")
        for table in ("suppliers", "customers", "products", "orders", "order_items", "payments", "shipments", "inventory_movements"):
            conn.execute(psycopg.sql.SQL("CREATE TABLE edge_cases.{} (LIKE commerce.{} INCLUDING ALL)").format(
                psycopg.sql.Identifier(table), psycopg.sql.Identifier(table)))
            conn.execute(psycopg.sql.SQL("INSERT INTO edge_cases.{} SELECT * FROM commerce.{} WHERE id<=30").format(
                psycopg.sql.Identifier(table), psycopg.sql.Identifier(table)))
        conn.execute("UPDATE edge_cases.orders SET customer_id=CASE WHEN id<20 THEN 1 ELSE NULL END, total=0")
        conn.execute("UPDATE edge_cases.customers SET region=NULL WHERE id%2=0")
        conn.execute("GRANT SELECT ON ALL TABLES IN SCHEMA commerce, edge_cases TO pgo_reader")

        conn.execute("DROP SCHEMA IF EXISTS edge_empty CASCADE; CREATE SCHEMA edge_empty AUTHORIZATION pgo_experiment")
        conn.execute("GRANT USAGE ON SCHEMA edge_empty TO pgo_reader")
        for table in ("suppliers", "customers", "products", "orders", "order_items", "payments", "shipments", "inventory_movements"):
            conn.execute(psycopg.sql.SQL("CREATE TABLE edge_empty.{} (LIKE commerce.{} INCLUDING ALL)").format(
                psycopg.sql.Identifier(table), psycopg.sql.Identifier(table)))
        conn.execute("GRANT SELECT ON ALL TABLES IN SCHEMA edge_empty TO pgo_reader")
