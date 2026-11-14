"""Positive SQL policy for a controlled schema, independent of model output."""
import hashlib

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

TABLES = frozenset({"customers", "products", "orders", "order_items", "payments",
                    "inventory_movements", "suppliers", "shipments"})
FUNCTIONS = frozenset({"AND", "OR", "COUNT", "SUM", "AVG", "MIN", "MAX", "COALESCE", "NULLIF", "ABS",
                      "ROUND", "LOWER", "UPPER", "LENGTH", "EXTRACT", "DATE_TRUNC",
                      "CAST", "TRY_CAST", "CASE", "IF", "ROW_NUMBER", "RANK", "DENSE_RANK",
                      "GREATEST", "LEAST", "POWER", "FLOOR", "CEIL", "CEILING"})
# Every accepted node is data-only syntax. Unknown extensions fail closed.
NODES = frozenset("""Select Subquery Union Intersect Except With CTE Table TableAlias Column
Identifier Star Literal Null Boolean Alias From Join Where And Or Not Paren EQ NEQ GT GTE LT LTE
Add Sub Mul Div Mod Neg In Between Is Like ILike Exists Distinct Group Having Order Ordered
Limit Offset Tuple Case If When Window WindowSpec Partition Having DataType DataTypeParam
Interval Var Cast TryCast Count Sum Avg Min Max Coalesce Nullif Abs Round Lower Upper Length
Extract DateTrunc TimestampTrunc RowNumber Rank DenseRank Greatest Least Pow Floor Ceil
Filter WithinGroup Fetch Lateral""".split())


class UnsafeSQL(ValueError):
    pass


def validate(sql: str, schema: str = "commerce") -> exp.Query:
    if len(sql.encode()) > 20000:
        raise UnsafeSQL("SQL exceeds byte limit")
    try:
        statements = sqlglot.parse(sql, read="postgres")
    except ParseError as exc:
        raise UnsafeSQL("Invalid PostgreSQL syntax") from exc
    if len(statements) != 1 or not isinstance(statements[0], (exp.Select, exp.Union, exp.Intersect, exp.Except)):
        raise UnsafeSQL("Exactly one SELECT query is required")
    tree = statements[0]
    ctes = {cte.alias_or_name for cte in tree.find_all(exp.CTE)}
    for node in tree.walk():
        if node.__class__.__name__ not in NODES:
            raise UnsafeSQL(f"Unsupported SQL syntax: {node.__class__.__name__}")
        if isinstance(node, exp.Func) and node.sql_name() not in FUNCTIONS:
            raise UnsafeSQL(f"Function is not allowed: {node.sql_name()}")
        if isinstance(node, exp.Table):
            if node.catalog or node.db not in ("", schema):
                raise UnsafeSQL("Schema is not allowed")
            if node.name not in TABLES and not (node.name in ctes and not node.db):
                raise UnsafeSQL("Relation is not allowed")
        if isinstance(node, exp.With) and node.args.get("recursive"):
            raise UnsafeSQL("Recursive queries are not supported")
    return tree


def normalize(sql: str) -> str:
    return validate(sql).sql(dialect="postgres", pretty=False)


def fingerprint(sql: str) -> str:
    return hashlib.sha256(normalize(sql).encode()).hexdigest()


def structure(sql: str) -> dict[str, str]:
    tree = validate(sql)
    keys = ("expressions", "where", "joins", "group", "having", "order", "limit", "offset", "distinct")
    return {key: str(tree.args.get(key)) for key in keys}


def order_compatible(original: str, candidate: str) -> bool:
    left, right = validate(original), validate(candidate)
    # Conservative contract: preserve the full ordering, pagination and DISTINCT syntax.
    for key in ("order", "limit", "offset", "distinct"):
        if str(left.args.get(key)) != str(right.args.get(key)):
            return False
    for tree in (left, right):
        if (tree.args.get("limit") or tree.args.get("offset")) and not tree.args.get("order"):
            return False
    return True
