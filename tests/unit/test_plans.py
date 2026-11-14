import unittest

from optimizer.plans import compare_plans, diagnose, flatten


class PlanTests(unittest.TestCase):
    def test_missing_fields(self):
        self.assertEqual(diagnose({"Plan": {"Node Type": "Result"}}), [])

    def test_nested_paths(self):
        self.assertEqual(
            [x["path"] for x in flatten({"Plan": {"Plans": [{}, {}]}})], ["0", "0.0", "0.1"]
        )

    def test_selective_scan(self):
        codes = {
            d["code"]
            for d in diagnose(
                {
                    "Plan": {
                        "Node Type": "Seq Scan",
                        "Actual Rows": 10,
                        "Rows Removed by Filter": 100000,
                    }
                }
            )
        }
        self.assertIn("selective_scan", codes)

    def test_full_scan_not_automatically_bad(self):
        self.assertEqual(
            diagnose(
                {"Plan": {"Node Type": "Seq Scan", "Actual Rows": 100000, "Plan Rows": 100000}}
            ),
            [],
        )

    def test_cardinality(self):
        self.assertEqual(
            diagnose({"Plan": {"Plan Rows": 10, "Actual Rows": 10000}})[0]["code"], "cardinality"
        )

    def test_spill(self):
        self.assertIn(
            "spill",
            {
                d["code"]
                for d in diagnose({"Plan": {"Node Type": "Sort", "Sort Space Type": "Disk"}})
            },
        )

    def test_buffer_delta_not_sum(self):
        result = compare_plans(
            {"Plan": {"Shared Hit Blocks": 20, "Plans": [{"Shared Hit Blocks": 20}]}},
            {"Plan": {"Shared Hit Blocks": 5}},
        )
        self.assertEqual(result["shared_hits_delta"], -15)
