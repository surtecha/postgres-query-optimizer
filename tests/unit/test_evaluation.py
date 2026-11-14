import unittest
from optimizer.evaluation_metrics import aggregate


class EvaluationTests(unittest.TestCase):
    def test_missing_arm_not_a_success(self):
        result=aggregate([{"provider":"openai","status":"not_run"}])["openai"]
        self.assertEqual(result['executed_workloads'],0)
        self.assertIsNone(result['valid_candidate_rate'])
        self.assertIsNone(result['tokens'])

    def test_measured_rates(self):
        rows=[{'provider':'deterministic','session':{'status':'completed','report':{
            'decision':'validated_improvement','duration_seconds':2,
            'model_usage':{'calls':0,'tokens':0,'estimated_cost_usd':0},
            'candidates':[{'safety':{'passed':True},'validation':{'status':'differentially_validated'},
                           'accepted':True,'benchmark':{'median_speedup':2,'runs':[{'latency_ms':5}]}},
                          {'safety':{'passed':False},'accepted':False}]}}}]
        result=aggregate(rows)['deterministic']
        self.assertEqual(result['valid_candidate_rate'],.5)
        self.assertEqual(result['candidate_acceptance_rate'],.5)
        self.assertEqual(result['median_accepted_speedup'],2)
        self.assertEqual(result['database_execution_ms'],5)

    def test_failure_not_counted_as_completed(self):
        result=aggregate([{'provider':'deterministic','session':{'status':'failed'}}])['deterministic']
        self.assertEqual(result['completed_workloads'],0)
        self.assertIsNone(result['workloads_improved_rate'])
