from decimal import Decimal
import unittest

from optimizer.results import equal_rows


class BagTests(unittest.TestCase):
    def test_duplicates_preserved(self):
        self.assertFalse(equal_rows([(1,), (1,)], [(1,), (2,)], False))

    def test_bag_order_independent(self):
        self.assertTrue(equal_rows([(1,), (2,), (1,)], [(1,), (1,), (2,)], False))

    def test_ordered_results(self):
        self.assertFalse(equal_rows([(1,), (2,)], [(2,), (1,)], True))

    def test_null_is_not_text(self):
        self.assertFalse(equal_rows([(None,)], [('None',)], False))

    def test_numeric_precision(self):
        self.assertFalse(equal_rows([(Decimal('1.00000000001'),)], [(Decimal('1.00000000002'),)], False))

    def test_types_preserved(self):
        self.assertFalse(equal_rows([(1,)], [(1.0,)], False))

    def test_empty(self):
        self.assertTrue(equal_rows([], [], False))

    def test_empty_vs_null(self):
        self.assertFalse(equal_rows([], [(None,)], False))

    def test_nested(self):
        self.assertTrue(equal_rows([([1,None],)], [([1,None],)], False))
