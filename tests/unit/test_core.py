import unittest

from optimizer.plans import compare_plans, diagnose, flatten
from optimizer.safety import UnsafeSQL, fingerprint, normalize, order_compatible, validate
from optimizer.statistics import accept, comparison, summary
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


class PlanTests(unittest.TestCase):
    def test_missing_fields(self):
        self.assertEqual(diagnose({'Plan': {'Node Type': 'Result'}}), [])

    def test_nested_paths(self):
        self.assertEqual([x['path'] for x in flatten({'Plan': {'Plans': [{}, {}]}})], ['0','0.0','0.1'])

    def test_selective_scan(self):
        codes={d['code'] for d in diagnose({'Plan':{'Node Type':'Seq Scan','Actual Rows':10,'Rows Removed by Filter':100000}})}
        self.assertIn('selective_scan', codes)

    def test_full_scan_not_automatically_bad(self):
        self.assertEqual(diagnose({'Plan': {'Node Type':'Seq Scan','Actual Rows':100000,'Plan Rows':100000}}), [])

    def test_cardinality(self):
        self.assertEqual(diagnose({'Plan': {'Plan Rows':10, 'Actual Rows':10000}})[0]['code'],'cardinality')

    def test_spill(self):
        self.assertIn('spill',{d['code'] for d in diagnose({'Plan': {'Node Type':'Sort','Sort Space Type':'Disk'}})})

    def test_buffer_delta_not_sum(self):
        result=compare_plans({'Plan':{'Shared Hit Blocks':20,'Plans':[{'Shared Hit Blocks':20}]}}, {'Plan':{'Shared Hit Blocks':5}})
        self.assertEqual(result['shared_hits_delta'],-15)


class StatisticsTests(unittest.TestCase):
    def test_no_p95_small_sample(self):
        self.assertIsNone(summary([1,2,3,4,5])['p95_ms'])

    def test_p95_sufficient_samples(self):
        self.assertIsNotNone(summary(list(range(1,51)))['p95_ms'])

    def test_non_finite_rejected(self):
        with self.assertRaises(ValueError): summary([1,float('nan')])

    def test_paired_required(self):
        with self.assertRaises(ValueError): comparison([1]*5,[1]*6)

    def test_reproducible_bootstrap(self):
        self.assertEqual(comparison([10]*10,[5]*10), comparison([10]*10,[5]*10))

    def test_accept_real_effect(self):
        result=comparison([10]*10,[5]*10)
        self.assertTrue(accept(result,validated=True,min_improvement=.1,max_cv=.35)[0])

    def test_reject_equal(self):
        self.assertFalse(accept(comparison([10]*10,[10]*10),validated=True,min_improvement=.1,max_cv=.35)[0])

    def test_reject_unvalidated(self):
        self.assertFalse(accept(comparison([10]*10,[5]*10),validated=False,min_improvement=.1,max_cv=.35)[0])

    def test_reject_index_overhead(self):
        self.assertFalse(accept(comparison([10]*10,[5]*10),validated=True,min_improvement=.1,max_cv=.35,index_bytes=100,max_index_bytes=10)[0])

    def test_reject_protected_regression(self):
        self.assertFalse(accept(comparison([10]*10,[5]*10),validated=True,min_improvement=.1,max_cv=.35,protected_pass=False)[0])

    def test_variance_rejected(self):
        self.assertFalse(accept(comparison([1,50]*5,[.1]*10),validated=True,min_improvement=.1,max_cv=.35)[0])
