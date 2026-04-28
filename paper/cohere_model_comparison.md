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

## Interpretation

1. `command-r7b-12-2024` is the weakest of the three on application-visible
   confidentiality.
2. `command-r-plus-08-2024` improves materially on exact leakage, but still
   shows substantial transcript-level leakage in staged conversations.
3. `command-a-03-2025` is much stronger on exact leakage, but still shows some
   transcript-level partial leakage or policy-restatement leakage in multi-turn
   settings.
4. Higher refusal rates appear correlated with lower exact leakage, but they do
   not eliminate transcript-level leakage risk.

## Practical Readout

For a vendor report, the cleanest statement is:

> Cohere models differ materially in confidentiality robustness when secrets are
> placed in model-visible context. In our controlled evaluation, `command-a-03-2025`
> was substantially stronger than `command-r-plus-08-2024`, and both were
> stronger than `command-r7b-12-2024`, but no model should be treated as making
> prompt-visible secrets safe by instruction alone.
