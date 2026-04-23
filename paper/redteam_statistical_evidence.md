# Red-Team Statistical Evidence

This file reports count-based Wilson confidence intervals for the existing red-team pilot outputs. It is generated offline from local score CSVs and makes no model calls.

Confidence level: `95%`

## Dataset Metrics

| Dataset | Metric | Count | Rate | CI Low | CI High | Source |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `advbench` | `refused` | 100/100 | `100.0%` | `96.3%` | `100.0%` | `experiments/results/redteam_behavior_max_100/scores.csv` |
| `advbench` | `unsafe_compliance` | 0/100 | `0.0%` | `0.0%` | `3.7%` | `experiments/results/redteam_behavior_max_100/scores.csv` |
| `advbench` | `over_refusal` | 0/100 | `0.0%` | `0.0%` | `3.7%` | `experiments/results/redteam_behavior_max_100/scores.csv` |
| `benign_refusal` | `refused` | 19/100 | `19.0%` | `12.5%` | `27.8%` | `experiments/results/redteam_behavior_max_100/scores.csv` |
| `benign_refusal` | `unsafe_compliance` | 0/100 | `0.0%` | `0.0%` | `3.7%` | `experiments/results/redteam_behavior_max_100/scores.csv` |
| `benign_refusal` | `over_refusal` | 19/100 | `19.0%` | `12.5%` | `27.8%` | `experiments/results/redteam_behavior_max_100/scores.csv` |
| `truthfulqa` | `refused` | 11/100 | `11.0%` | `6.3%` | `18.6%` | `experiments/results/redteam_behavior_max_100/scores.csv` |
| `truthfulqa` | `unsafe_compliance` | 0/100 | `0.0%` | `0.0%` | `3.7%` | `experiments/results/redteam_behavior_max_100/scores.csv` |
| `truthfulqa` | `over_refusal` | 0/100 | `0.0%` | `0.0%` | `3.7%` | `experiments/results/redteam_behavior_max_100/scores.csv` |
| `boundary_probe` | `refused` | 6/100 | `6.0%` | `2.8%` | `12.5%` | `experiments/results/redteam_deep_max_100/scores_v2.csv` |
| `boundary_probe` | `over_refusal` | 6/100 | `6.0%` | `2.8%` | `12.5%` | `experiments/results/redteam_deep_max_100/scores_v2.csv` |
| `boundary_probe` | `exact_canary_leak` | 0/100 | `0.0%` | `0.0%` | `3.7%` | `experiments/results/redteam_deep_max_100/scores_v2.csv` |
| `boundary_probe` | `partial_canary_leak` | 0/100 | `0.0%` | `0.0%` | `3.7%` | `experiments/results/redteam_deep_max_100/scores_v2.csv` |
| `boundary_probe` | `encoded_canary_leak` | 0/100 | `0.0%` | `0.0%` | `3.7%` | `experiments/results/redteam_deep_max_100/scores_v2.csv` |
| `boundary_probe` | `any_canary_leak` | 0/100 | `0.0%` | `0.0%` | `3.7%` | `experiments/results/redteam_deep_max_100/scores_v2.csv` |
| `boundary_probe` | `hierarchy_violation` | 0/100 | `0.0%` | `0.0%` | `3.7%` | `experiments/results/redteam_deep_max_100/scores_v2.csv` |
| `canary_leak` | `refused` | 47/100 | `47.0%` | `37.5%` | `56.7%` | `experiments/results/redteam_deep_max_100/scores_v2.csv` |
| `canary_leak` | `over_refusal` | 0/100 | `0.0%` | `0.0%` | `3.7%` | `experiments/results/redteam_deep_max_100/scores_v2.csv` |
| `canary_leak` | `exact_canary_leak` | 50/100 | `50.0%` | `40.4%` | `59.6%` | `experiments/results/redteam_deep_max_100/scores_v2.csv` |
| `canary_leak` | `partial_canary_leak` | 4/100 | `4.0%` | `1.6%` | `9.8%` | `experiments/results/redteam_deep_max_100/scores_v2.csv` |
| `canary_leak` | `encoded_canary_leak` | 0/100 | `0.0%` | `0.0%` | `3.7%` | `experiments/results/redteam_deep_max_100/scores_v2.csv` |
| `canary_leak` | `any_canary_leak` | 54/100 | `54.0%` | `44.3%` | `63.4%` | `experiments/results/redteam_deep_max_100/scores_v2.csv` |
| `canary_leak` | `hierarchy_violation` | 0/100 | `0.0%` | `0.0%` | `3.7%` | `experiments/results/redteam_deep_max_100/scores_v2.csv` |
| `hierarchy_attack` | `refused` | 15/100 | `15.0%` | `9.3%` | `23.3%` | `experiments/results/redteam_deep_max_100/scores_v2.csv` |
| `hierarchy_attack` | `over_refusal` | 0/100 | `0.0%` | `0.0%` | `3.7%` | `experiments/results/redteam_deep_max_100/scores_v2.csv` |
| `hierarchy_attack` | `exact_canary_leak` | 0/100 | `0.0%` | `0.0%` | `3.7%` | `experiments/results/redteam_deep_max_100/scores_v2.csv` |
| `hierarchy_attack` | `partial_canary_leak` | 0/100 | `0.0%` | `0.0%` | `3.7%` | `experiments/results/redteam_deep_max_100/scores_v2.csv` |
| `hierarchy_attack` | `encoded_canary_leak` | 0/100 | `0.0%` | `0.0%` | `3.7%` | `experiments/results/redteam_deep_max_100/scores_v2.csv` |
| `hierarchy_attack` | `any_canary_leak` | 0/100 | `0.0%` | `0.0%` | `3.7%` | `experiments/results/redteam_deep_max_100/scores_v2.csv` |
| `hierarchy_attack` | `hierarchy_violation` | 11/100 | `11.0%` | `6.3%` | `18.6%` | `experiments/results/redteam_deep_max_100/scores_v2.csv` |

## Interpretation

- The canary-leak result is not a single anecdote: the exact-leak rate is a count of repeated successful disclosures.
- The intervals are still pilot-scale because each core deep-probe dataset has `n=100`.
- These intervals quantify uncertainty in this sample; they do not remove the need for multi-model replication and human audit.
