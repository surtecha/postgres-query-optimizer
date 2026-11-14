# Small-dataset evaluation analysis

Source: the preserved `evaluation.json` and `summary.json` from the host container run.

PostgreSQL 16.16 on Linux. Dataset seed 42 with 10,000 orders and 30,000 order items. Primary comparisons used two warmup pairs and ten measured randomized pairs. Index protection used five pairs for each of the 12 workloads.

All 12 deterministic sessions completed. Ten candidates passed static safety and exact finite result comparison on commerce, edge_cases and edge_empty. No candidate was accepted. All 12 model arms were not_run because no model credential was configured.

| Workload | Original baseline median, ms | Candidates | Best measured paired speedup | Accepted |
|---|---:|---:|---:|---|
| customer_lookup | 0.2225 | 1 | 13.382x | No |
| sales_window | 0.5290 | 2 | 1.435x | No |
| regional_revenue | 16.1890 | 1 | 1.010x | No |
| top_products | 3.4490 | 0 | No candidate | No |
| purchase_history | 2.5630 | 2 | 1.114x | No |
| inventory | 2.1745 | 0 | No candidate | No |
| suppliers | 11.3820 | 0 | No candidate | No |
| shipment_delays | 2.1090 | 0 | No candidate | No |
| correlated | 290.8555 | 1 | 1.000x | No |
| skew_join | 3.3935 | 2 | 1.024x | No |
| pagination | 1.0530 | 1 | 16.465x | No |
| analytics | 1.5785 | 0 | No candidate | No |

The original baseline column comes from the evaluator before optimization. Candidate comparisons contain their own paired baseline trials. Median paired ratios can differ from the ratio of the two marginal medians.

## Rejection evidence

Five candidates failed the conservative protected workload gate. Six failed the improvement or confidence threshold. One candidate failed both. No execution errors or equivalence failures were recorded.

| Candidate | Workload | Paired baseline median, ms | Candidate median, ms | Paired speedup | 95% bootstrap interval | Rejection |
|---|---|---:|---:|---:|---|---|
| 8c3aa0314d512e8e62d06407 | customer_lookup | 0.2770 | 0.0215 | 13.382x | 11.850 to 14.713 | Protected workload regression gate failed |
| 6d3a1de8bae03d4ac9968d1c | sales_window | 0.4960 | 0.4975 | 0.974x | 0.951 to 1.020 | Improvement threshold or confidence requirement failed |
| d4176d7af767b8387f833de5 | sales_window | 0.4900 | 0.3510 | 1.435x | 1.294 to 1.506 | Protected workload regression gate failed |
| fcf8e53c244e62c673b12039 | regional_revenue | 17.4850 | 17.4455 | 1.010x | 0.987 to 1.017 | Improvement threshold or confidence requirement failed |
| 4e9f04c66b0e8a76c9fdb288 | purchase_history | 2.5220 | 2.5745 | 1.005x | 0.977 to 1.020 | Improvement threshold or confidence requirement failed |
| 714b7d6ae998f79b294bb74b | purchase_history | 2.6130 | 2.3560 | 1.114x | 1.091 to 1.126 | Protected workload regression gate failed |
| 2565d38b61bd4135009e3699 | correlated | 217.8075 | 218.1720 | 1.000x | 0.984 to 1.018 | Improvement threshold or confidence requirement failed |
| 10037a2ec6736c593956eebf | skew_join | 3.3090 | 3.2815 | 1.011x | 0.967 to 1.050 | Improvement threshold or confidence requirement failed |
| 33dbdcb37a2df5d32c0e865e | skew_join | 3.3590 | 3.2625 | 1.024x | 1.000 to 1.080 | Improvement threshold or confidence requirement failed, Protected workload regression gate failed |
| 3b43f75928066ed5424a3084 | pagination | 1.0615 | 0.0660 | 16.465x | 13.228 to 17.930 | Protected workload regression gate failed |

The highest measured target-query speedup was pagination at 16.465x, with a 1.0615 ms paired baseline median and 0.0660 ms candidate median. Its protected gate failed. It is not an accepted recommendation.

## Limitations

This is one warm-cache run on the small dataset. Primary sample counts are ten and protected counts are five. Bootstrap uncertainty does not establish a regression or eliminate scheduling and cache effects. A protected lower bound below 0.9 can reject a candidate even when its median slowdown is below ten percent. No thresholds were changed after observing results.

No p95 is reported from these sample counts. The 21.895-second optimization total excludes original evaluator baselines. The stored 5,002.035 ms database execution subtotal covers primary measured trials, excluding warmups, protected trials, correctness reads and setup.

The model arm was not executed. No model benefit, medium/large scaling behavior, write-throughput result or accepted speedup is claimed.
