import unittest

from optimizer.safety import UnsafeSQL, fingerprint, normalize, order_compatible, validate
from optimizer.workloads import WORKLOADS


class SafetyTests(unittest.TestCase):
    def test_all_workloads_parse(self):
        for workload in WORKLOADS:
            with self.subTest(workload=workload['id']):
                validate(workload['sql'])

    def test_writes_rejected(self):
        for query in ["DELETE FROM commerce.orders", "UPDATE commerce.orders SET total=0", "DROP TABLE commerce.orders",
                      "INSERT INTO commerce.orders VALUES(1)", "CREATE INDEX i ON commerce.orders(id)",
                      "COPY commerce.orders TO '/tmp/evil'", "VACUUM commerce.orders"]:
            with self.subTest(query=query), self.assertRaises(UnsafeSQL):
                validate(query)

    def test_multiple_statements_rejected(self):
        with self.assertRaises(UnsafeSQL): validate("SELECT 1; SELECT 2")

    def test_system_schema_rejected(self):
        for query in ["SELECT * FROM pg_catalog.pg_class", "SELECT * FROM information_schema.tables",
                      "SELECT * FROM public.orders", "SELECT * FROM other.commerce.orders"]:
            with self.subTest(query=query), self.assertRaises(UnsafeSQL): validate(query)

    def test_unknown_relation_rejected(self):
        with self.assertRaises(UnsafeSQL): validate("SELECT * FROM secrets")

    def test_side_effect_functions_rejected(self):
        for query in ["SELECT pg_sleep(1)", "SELECT set_config('search_path','public',false)",
                      "SELECT nextval('x')", "SELECT dblink('x','DELETE FROM x')", "SELECT pg_read_file('/etc/passwd')",
                      "SELECT commerce.sum(total) FROM commerce.orders"]:
            with self.subTest(query=query), self.assertRaises(UnsafeSQL): validate(query)

    def test_into_and_lock_rejected(self):
        for query in ["SELECT * INTO other FROM commerce.orders", "SELECT * FROM commerce.orders FOR UPDATE"]:
            with self.subTest(query=query), self.assertRaises(UnsafeSQL): validate(query)

    def test_data_modifying_cte_rejected(self):
        with self.assertRaises(UnsafeSQL): validate("WITH x AS (DELETE FROM commerce.orders RETURNING *) SELECT * FROM x")

    def test_recursive_rejected(self):
        with self.assertRaises(UnsafeSQL): validate("WITH RECURSIVE x AS (SELECT 1 UNION ALL SELECT 1 FROM x) SELECT * FROM x")

    def test_size_limit(self):
        with self.assertRaises(UnsafeSQL): validate("SELECT '" + "a"*20000 + "'")

    def test_normalization(self):
        self.assertEqual(normalize("select id from commerce.orders"), normalize("SELECT id FROM commerce.orders"))

    def test_fingerprint(self):
        self.assertEqual(len(fingerprint("SELECT 1")),64)

    def test_cte(self):
        validate("WITH x AS (SELECT id FROM commerce.orders) SELECT * FROM x")

    def test_changed_order_rejected(self):
        self.assertFalse(order_compatible("SELECT id FROM commerce.orders ORDER BY id", "SELECT id FROM commerce.orders ORDER BY id DESC"))

    def test_unordered_limit_inconclusive(self):
        self.assertFalse(order_compatible("SELECT id FROM commerce.orders LIMIT 1", "SELECT id FROM commerce.orders LIMIT 1"))

    def test_changed_distinct_rejected(self):
        self.assertFalse(order_compatible("SELECT id FROM commerce.orders", "SELECT DISTINCT id FROM commerce.orders"))

    def test_comments_do_not_bypass(self):
        with self.assertRaises(UnsafeSQL): validate("SELECT 1; -- safe\nDELETE FROM commerce.orders")
