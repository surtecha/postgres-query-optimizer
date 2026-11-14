CREATE TABLE IF NOT EXISTS commerce.suppliers (
 id bigint PRIMARY KEY, name text NOT NULL, region text NOT NULL
);
CREATE TABLE IF NOT EXISTS commerce.customers (
 id bigint PRIMARY KEY, email text UNIQUE NOT NULL, region text, created_at date NOT NULL
);
CREATE TABLE IF NOT EXISTS commerce.products (
 id bigint PRIMARY KEY, supplier_id bigint REFERENCES commerce.suppliers,
 name text NOT NULL, category text NOT NULL, price numeric(12,2) NOT NULL CHECK (price >= 0)
);
CREATE TABLE IF NOT EXISTS commerce.orders (
 id bigint PRIMARY KEY, customer_id bigint REFERENCES commerce.customers,
 ordered_at timestamp NOT NULL, status text NOT NULL,
 total numeric(14,2) NOT NULL CHECK (total >= 0)
);
CREATE TABLE IF NOT EXISTS commerce.order_items (
 id bigint PRIMARY KEY, order_id bigint NOT NULL REFERENCES commerce.orders,
 product_id bigint NOT NULL REFERENCES commerce.products, quantity integer NOT NULL CHECK (quantity > 0),
 unit_price numeric(12,2) NOT NULL CHECK (unit_price >= 0)
);
CREATE TABLE IF NOT EXISTS commerce.payments (
 id bigint PRIMARY KEY, order_id bigint NOT NULL REFERENCES commerce.orders,
 amount numeric(14,2) NOT NULL, method text NOT NULL, paid_at timestamp
);
CREATE TABLE IF NOT EXISTS commerce.shipments (
 id bigint PRIMARY KEY, order_id bigint NOT NULL REFERENCES commerce.orders,
 shipped_at timestamp, delivered_at timestamp, expected_at timestamp NOT NULL
);
CREATE TABLE IF NOT EXISTS commerce.inventory_movements (
 id bigint PRIMARY KEY, product_id bigint NOT NULL REFERENCES commerce.products,
 quantity integer NOT NULL, moved_at timestamp NOT NULL
);
CREATE TABLE IF NOT EXISTS commerce.dataset_manifest (
 singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton), seed integer NOT NULL,
 orders_count integer NOT NULL, generated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);
