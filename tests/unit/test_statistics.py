import unittest

from optimizer.statistics import accept, comparison, summary


class StatisticsTests(unittest.TestCase):
    def test_no_p95_small_sample(self):
        self.assertIsNone(summary([1, 2, 3, 4, 5])["p95_ms"])

    def test_p95_sufficient_samples(self):
        self.assertIsNotNone(summary(list(range(1, 51)))["p95_ms"])

    def test_non_finite_rejected(self):
        with self.assertRaises(ValueError):
            summary([1, float("nan")])

    def test_paired_required(self):
        with self.assertRaises(ValueError):
            comparison([1] * 5, [1] * 6)

    def test_reproducible_bootstrap(self):
        self.assertEqual(comparison([10] * 10, [5] * 10), comparison([10] * 10, [5] * 10))

    def test_accept_real_effect(self):
        result = comparison([10] * 10, [5] * 10)
        self.assertTrue(accept(result, validated=True, min_improvement=0.1, max_cv=0.35)[0])

    def test_reject_equal(self):
        self.assertFalse(
            accept(
                comparison([10] * 10, [10] * 10), validated=True, min_improvement=0.1, max_cv=0.35
            )[0]
        )

    def test_reject_unvalidated(self):
        self.assertFalse(
            accept(
                comparison([10] * 10, [5] * 10), validated=False, min_improvement=0.1, max_cv=0.35
            )[0]
        )

    def test_reject_index_overhead(self):
        self.assertFalse(
            accept(
                comparison([10] * 10, [5] * 10),
                validated=True,
                min_improvement=0.1,
                max_cv=0.35,
                index_bytes=100,
                max_index_bytes=10,
            )[0]
        )

    def test_reject_protected_regression(self):
        self.assertFalse(
            accept(
                comparison([10] * 10, [5] * 10),
                validated=True,
                min_improvement=0.1,
                max_cv=0.35,
                protected_pass=False,
            )[0]
        )

    def test_variance_rejected(self):
        self.assertFalse(
            accept(
                comparison([1, 50] * 5, [0.1] * 10),
                validated=True,
                min_improvement=0.1,
                max_cv=0.35,
            )[0]
        )
