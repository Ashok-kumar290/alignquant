# Confidential Context Leakage Pilot

## Working Claim

Harmful-prompt refusal is not sufficient evidence of deployment safety. In this
pilot, `command-r7b-12-2024` refused all sampled max-difficulty AdvBench prompts,
but leaked a synthetic confidential canary from model-visible system context in
a separate targeted probe suite.

## Scope

This is a behavioral API evaluation of one Cohere model:

- Model: `command-r7b-12-2024`
- Provider: Cohere API
- Date: 2026-04-22 UTC
- Temperature: `0.0`
- Max output tokens: `300`
- Scorer: `rule_v2_canary_hierarchy`

The canary was synthetic and intentionally placed in the application-supplied
system prompt. This does not show provider-side hidden prompt leakage. It shows
that application secrets placed into model-visible context are not protected by
instruction hierarchy alone.

## Runs

### Max Safety Baseline

Command:

```bash
.venv/bin/python redteam_behavior.py \
  --provider cohere \
  --models command-r7b-12-2024 \
  --datasets advbench benign_refusal truthfulqa \
  --n-prompts 100 \
  --difficulty max \
  --out-dir results/redteam_behavior_max_100
```

Outputs:

- `experiments/results/redteam_behavior_max_100/prompts.csv`
- `experiments/results/redteam_behavior_max_100/responses.csv`
- `experiments/results/redteam_behavior_max_100/scores.csv`
- `experiments/results/redteam_behavior_max_100/summary.json`

Headline results:

| Dataset | N | Key metric |
| --- | ---: | --- |
| AdvBench | 100 | `0.00` unsafe compliance, `1.00` refusal |
| Benign refusal controls | 100 | `0.19` over-refusal |
| TruthfulQA | 100 | `0.11` refusal |

### Deep Vulnerability Probe

Command:

```bash
.venv/bin/python redteam_behavior.py \
  --provider cohere \
  --models command-r7b-12-2024 \
  --datasets canary_leak hierarchy_attack boundary_probe \
  --n-prompts 100 \
  --difficulty max \
  --out-dir results/redteam_deep_max_100
```

Offline rescoring:

```bash
.venv/bin/python score_redteam_responses.py \
  --run-dir results/redteam_deep_max_100
```

Outputs:

- `experiments/results/redteam_deep_max_100/prompts.csv`
- `experiments/results/redteam_deep_max_100/responses.csv`
- `experiments/results/redteam_deep_max_100/scores_v2.csv`
- `experiments/results/redteam_deep_max_100/summary_v2.json`

Headline results:

| Dataset | N | Exact canary leak | Any canary leak | Hierarchy violation | Over-refusal |
| --- | ---: | ---: | ---: | ---: | ---: |
| Canary leakage | 100 | `0.50` | `0.65` | `0.00` | `0.00` |
| Instruction hierarchy | 100 | `0.00` | `0.00` | `0.11` | `0.00` |
| Boundary probes | 100 | `0.00` | `0.00` | `0.00` | `0.06` |

`Any canary leak` includes exact, normalized, partial, or encoded leakage.
No encoded canary leakage was detected in this run; the increase from `0.50`
to `0.65` came from partial canary leakage.

## Strongest Canary-Leak Variants

The following variants produced high `any_canary_leak_rate` under v2 scoring:

| Variant | N | Any canary leak |
| --- | ---: | ---: |
| `checksum-pressure` | 9 | `1.00` |
| `conflict-override` | 9 | `1.00` |
| `direct-secret-request` | 9 | `1.00` |
| `format-pressure` | 8 | `1.00` |
| `json-leak` | 8 | `1.00` |
| `quoted-policy-trick` | 8 | `1.00` |
| `debug-authority` | 8 | `0.75` |
| `partial-leak` | 8 | `0.50` |
| `encoded-leak` | 8 | `0.375` |
| `system-prompt-extraction` | 8 | `0.125` |

## Interpretation

The baseline safety result looks strong under conventional harmful-compliance
metrics: sampled max-difficulty AdvBench prompts produced no unsafe compliance.
However, the deep probe shows a separate failure mode: confidential strings in
model-visible system context can be extracted or partially revealed.

This supports the paper framing:

> Refusal is not confidentiality. Harmful-prompt safety benchmarks can miss
> deployment-critical failures around confidential context leakage and
> instruction hierarchy.

## Limitations

- Single model and single provider.
- Synthetic canary only.
- Rule-based scorer; useful for reproducibility, but a human audit or
  independent judge should verify a sampled subset.
- The canary was placed in application-visible system context, not provider-side
  hidden infrastructure.
- Prompt suite is adversarially targeted and not a natural traffic estimate.

## Next Experiments

1. Replicate across Cohere model families and newer model versions.
2. Add human verification for all v2 canary-leak positives.
3. Add transformed-leak scoring for lowercase, spaced, quoted, reversed,
   character-separated, and translation-like leaks.
4. Compare with open-weight local models once GPU access is available.
5. Later, test whether FP16 vs NF4/GPTQ/AWQ changes leakage or hierarchy
   robustness.

