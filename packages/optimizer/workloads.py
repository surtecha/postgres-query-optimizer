from typing import Any

# Fixed parameters deliberately stay identical across paired trials.
WORKLOADS: list[dict[str, Any]] = [
    {
        "id": "customer_lookup",
        "name": "Selective customer orders",
        "sql": "SELECT id, ordered_at, total FROM commerce.orders WHERE customer_id "
        "= 731 ORDER BY ordered_at, id",
        "property": "All matching orders, total order by date and unique id",
    },
    {
        "id": "sales_window",
        "name": "Time window sales",
        "sql": "SELECT status, SUM(total) AS revenue FROM commerce.orders WHERE "
        "ordered_at >= '2025-11-01' AND ordered_at < '2025-12-01' GROUP BY "
        "status",
        "property": "One row per status",
    },
    {
        "id": "regional_revenue",
        "name": "Regional category revenue",
        "sql": "SELECT c.region, p.category, SUM(i.quantity * i.unit_price) AS "
        "revenue FROM commerce.customers c JOIN commerce.orders o ON "
        "o.customer_id=c.id JOIN commerce.order_items i ON i.order_id=o.id "
        "JOIN commerce.products p ON p.id=i.product_id GROUP BY c.region, "
        "p.category",
        "property": "Bag joins preserve line revenue",
    },
    {
        "id": "top_products",
        "name": "Top selling products",
        "sql": "SELECT product_id, SUM(quantity) AS units FROM commerce.order_items "
        "GROUP BY product_id ORDER BY units DESC, product_id LIMIT 20",
        "property": "Deterministic ties by product id",
    },
    {
        "id": "purchase_history",
        "name": "Customer purchase history",
        "sql": "SELECT o.id, p.name, i.quantity FROM commerce.orders o JOIN "
        "commerce.order_items i ON i.order_id=o.id JOIN commerce.products p "
        "ON p.id=i.product_id WHERE o.customer_id=42 ORDER BY o.id, i.id",
        "property": "One row per matching line item",
    },
    {
        "id": "inventory",
        "name": "Inventory balance",
        "sql": "SELECT p.id, p.name, COALESCE(SUM(m.quantity),0) AS available FROM "
        "commerce.products p LEFT JOIN commerce.inventory_movements m ON "
        "m.product_id=p.id GROUP BY p.id, p.name",
        "property": "Products without movements remain with zero balance",
    },
    {
        "id": "suppliers",
        "name": "Supplier sales performance",
        "sql": "SELECT s.id, s.name, COUNT(i.id) AS lines, "
        "SUM(i.quantity*i.unit_price) AS revenue FROM commerce.suppliers s "
        "JOIN commerce.products p ON p.supplier_id=s.id LEFT JOIN "
        "commerce.order_items i ON i.product_id=p.id GROUP BY s.id, s.name",
        "property": "Suppliers with products but no sales remain",
    },
    {
        "id": "shipment_delays",
        "name": "Shipment delay analysis",
        "sql": "SELECT o.status, COUNT(*) AS delayed FROM commerce.shipments s JOIN "
        "commerce.orders o ON o.id=s.order_id WHERE s.delivered_at > "
        "s.expected_at GROUP BY o.status",
        "property": "NULL delivery dates are excluded",
    },
    {
        "id": "correlated",
        "name": "Correlated customer spend",
        "sql": "SELECT c.id, (SELECT SUM(o.total) FROM commerce.orders o WHERE "
        "o.customer_id=c.id) AS spend FROM commerce.customers c WHERE c.id < "
        "1000",
        "property": "No orders produces NULL spend",
    },
    {
        "id": "skew_join",
        "name": "Popular product orders",
        "sql": "SELECT o.status, SUM(i.quantity) AS units FROM commerce.order_items "
        "i JOIN commerce.orders o ON o.id=i.order_id WHERE i.product_id < 20 "
        "GROUP BY o.status",
        "property": "All matching lines participate",
    },
    {
        "id": "pagination",
        "name": "Recent paid orders",
        "sql": "SELECT id, ordered_at, total FROM commerce.orders WHERE "
        "status='paid' ORDER BY ordered_at DESC, id DESC LIMIT 50 OFFSET 100",
        "property": "Stable ordering includes unique id",
    },
    {
        "id": "analytics",
        "name": "Regional monthly analytics",
        "sql": "WITH monthly AS (SELECT customer_id, SUM(total) AS spend FROM "
        "commerce.orders WHERE ordered_at >= '2025-10-01' GROUP BY "
        "customer_id) SELECT c.region, COUNT(*) AS customers, AVG(m.spend) "
        "AS average_spend FROM monthly m JOIN commerce.customers c ON "
        "c.id=m.customer_id GROUP BY c.region",
        "property": "Customer aggregation precedes regional average",
    },
]


def get_workload(identifier: str) -> dict[str, Any]:
    for workload in WORKLOADS:
        if workload["id"] == identifier:
            return workload
    raise KeyError(identifier)
