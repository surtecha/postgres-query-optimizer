from optimizer.equivalence import rebind
from sqlglot import exp, parse_one


def relations(query: str) -> list[tuple[str, str]]:
    return [
        (table.db, table.name) for table in parse_one(query, read="postgres").find_all(exp.Table)
    ]


def test_nested_cte_does_not_hide_outer_base_relation():
    query = (
        "SELECT id, (WITH orders AS (SELECT id FROM commerce.customers) "
        "SELECT COUNT(*) FROM orders) AS n FROM orders"
    )
    rebound = relations(rebind(query, "edge_cases"))
    assert ("edge_cases", "orders") in rebound
    assert ("edge_cases", "customers") in rebound
    assert ("", "orders") in rebound  # Only the scoped CTE reference remains unqualified.
    assert rebound.count(("", "orders")) == 1


def test_visible_cte_remains_a_cte():
    query = "WITH orders AS (SELECT id FROM commerce.customers) SELECT id FROM orders"
    rebound = relations(rebind(query, "edge_empty"))
    assert sorted(rebound) == [("", "orders"), ("edge_empty", "customers")]


def test_qualified_base_relation_bypasses_cte_shadowing():
    query = "WITH orders AS (SELECT id FROM commerce.customers) SELECT id FROM commerce.orders"
    assert sorted(relations(rebind(query, "edge_cases"))) == [
        ("edge_cases", "customers"),
        ("edge_cases", "orders"),
    ]


def test_derived_tables_rebind_their_own_base_relations():
    query = "SELECT x.id FROM (SELECT id FROM commerce.orders) x"
    assert relations(rebind(query, "edge_empty")) == [("edge_empty", "orders")]
