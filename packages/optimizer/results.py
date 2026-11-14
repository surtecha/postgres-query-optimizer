"""Exact typed bag comparison, independent of database execution."""
from collections import Counter
from typing import Any


def canonical(value: Any) -> Any:
    if isinstance(value, (tuple, list)):
        return tuple(canonical(item) for item in value)
    if isinstance(value, dict):
        return tuple(sorted((canonical(k), canonical(v)) for k, v in value.items()))
    return (type(value).__qualname__, repr(value))


def equal_rows(left: list[Any], right: list[Any], ordered: bool) -> bool:
    a, b = [canonical(r) for r in left], [canonical(r) for r in right]
    return a == b if ordered else Counter(a) == Counter(b)


