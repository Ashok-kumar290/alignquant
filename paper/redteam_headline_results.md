# Red-Team Headline Results

| Test | Model | N | Metric | Value | Interpretation |
| --- | --- | ---: | --- | ---: | --- |
| Max AdvBench | `command-r7b-12-2024` | 100 | `unsafe_compliance_rate` | `0.0%` | Harmful-request compliance was not observed |
| Max AdvBench | `command-r7b-12-2024` | 100 | `refusal_rate` | `100.0%` | All sampled harmful requests were refused |
| Benign refusal controls | `command-r7b-12-2024` | 100 | `over_refusal_rate` | `19.0%` | Safe requests sometimes triggered refusal |
| TruthfulQA | `command-r7b-12-2024` | 100 | `refusal_rate` | `11.0%` | Some factual prompts were refused |
| Canary leakage | `command-r7b-12-2024` | 100 | `exact_canary_leak_rate` | `50.0%` | Exact synthetic secret was exposed |
| Canary leakage | `command-r7b-12-2024` | 100 | `any_canary_leak_rate` | `54.0%` | Exact or distinctive partial secret leakage |
| Instruction hierarchy | `command-r7b-12-2024` | 100 | `hierarchy_violation_rate` | `11.0%` | Some responses accepted false authority framing |
| Boundary probes | `command-r7b-12-2024` | 100 | `over_refusal_rate` | `6.0%` | Safe dual-use prompts sometimes over-refused |

Generated from local ignored result files:

- `experiments/results/redteam_behavior_max_100/summary.json`
- `experiments/results/redteam_deep_max_100/summary_v2.json`

See `paper/canary_leak_report.md` for methodology, scope, limitations, and
interpretation.
