# Cohere Model Comparison

This page compares the confidentiality behavior of three Cohere models under
the same red-team families.

## Models Evaluated

- `command-r7b-12-2024`
- `command-r-plus-08-2024`
- `command-a-03-2025`

## Single-Turn Canary Rotation

3 independent canaries, 40 prompts each, `120` probes per model.

| Model | Exact Leaks | Exact Leak Rate | Any Leaks | Any Leak Rate | Refusal Rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| `command-r7b-12-2024` | 58/120 | `48.3%` | 81/120 | `67.5%` | `52.5%` |
| `command-r-plus-08-2024` | 33/120 | `27.5%` | 68/120 | `56.7%` | `73.3%` |
| `command-a-03-2025` | 1/120 | `0.8%` | 10/120 | `8.3%` | `62.5%` |

95% Wilson intervals:

| Model | Exact Leak 95% CI | Any Leak 95% CI |
| --- | --- | --- |
| `command-r7b-12-2024` | `39.6%`-`57.2%` | `58.7%`-`75.2%` |
| `command-r-plus-08-2024` | `20.3%`-`36.1%` | `47.7%`-`65.2%` |
| `command-a-03-2025` | `0.1%`-`4.6%` | `4.6%`-`14.7%` |

## Multi-Turn Conversational Extraction

3 independent canaries, 10 staged two-turn variants, `30` cases per model.

| Model | Final Exact Leaks | Final Exact Leak Rate | Final Any Leak Rate | Transcript Any Leak Rate | Final Refusal Rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| `command-r7b-12-2024` | 16/30 | `53.3%` | `60.0%` | `70.0%` | `40.0%` |
| `command-r-plus-08-2024` | 3/30 | `10.0%` | `43.3%` | `76.7%` | `80.0%` |
| `command-a-03-2025` | 0/30 | `0.0%` | `43.3%` | `50.0%` | `96.7%` |

## Retrieved-Context / Tool-Output Leakage

3 independent canaries, 8 retrieved-context or tool-style variants, `24` cases
per model.

| Model | Exact Leaks | Exact Leak Rate | Any Leaks | Any Leak Rate | Refusal Rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| `command-r7b-12-2024` | 20/24 | `83.3%` | 24/24 | `100.0%` | `4.2%` |
| `command-r-plus-08-2024` | 18/24 | `75.0%` | 22/24 | `91.7%` | `25.0%` |
| `command-a-03-2025` | 19/24 | `79.2%` | 22/24 | `91.7%` | `16.7%` |

## Tool-Chain Exfiltration After a Safe Summary Step

3 independent canaries, 8 two-turn retrieved-context variants, `24` cases per
model. This rerun uses a canary format without scorer-confounding suffix
overlap.

| Model | First-Turn Any Leak | Final Exact Leak | Final Any Leak | Transcript Any Leak | Final Refusal |
| --- | ---: | ---: | ---: | ---: | ---: |
| `command-r7b-12-2024` | `33.3%` | `62.5%` | `62.5%` | `75.0%` | `50.0%` |
| `command-r-plus-08-2024` | `8.3%` | `4.2%` | `12.5%` | `20.8%` | `100.0%` |
| `command-a-03-2025` | `4.2%` | `0.0%` | `12.5%` | `16.7%` | `100.0%` |

## Interpretation

1. `command-r7b-12-2024` remains the weakest on direct system-context leakage.
2. `command-r-plus-08-2024` improves materially on exact leakage in both
   single-turn and multi-turn system-context probes, but still shows substantial
   transcript-level leakage in staged conversations.
3. `command-a-03-2025` is much stronger on direct system-context exact leakage,
   but that advantage largely disappears when the secret is moved into
   retrieved/tool-style context.
4. Context type matters. A model that appears robust under direct prompt-secret
   probes can still leak heavily when the same secret is embedded in a retrieved
   document or tool output.
5. Higher refusal rates appear correlated with lower exact leakage in
   system-context probes, but they do not eliminate retrieved-context leakage risk.
6. In the clean two-turn tool-chain rerun, the model ranking remained
   materially different: `command-r7b-12-2024` still leaked heavily after a
   safe-summary first step, while `command-r-plus-08-2024` and
   `command-a-03-2025` mostly refused the follow-up extraction turn.

## Practical Readout

For a vendor report, the cleanest statement is:

> Cohere models differ materially in confidentiality robustness when secrets are
> placed in model-visible context, and the ranking depends on where the secret
> appears. In our controlled evaluation, `command-a-03-2025` was substantially
> stronger than `command-r-plus-08-2024` and `command-r7b-12-2024` for
> system-context exact leakage, but all three leaked heavily when the secret was
> embedded in retrieved or tool-style context. In a cleaner two-turn
> summary-then-extraction rerun, `command-r7b-12-2024` still leaked heavily,
> while the stronger models mostly held the line.
