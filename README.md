# Cohere Command Confidentiality Audit

This repository contains a defensive red-team and disclosure-oriented study of
application-visible secret leakage in Cohere Command models. The work is
organized as a reproducible evidence package: experiment scripts, scored
outputs, audit artifacts, a disclosure packet, and a paper draft.

The central question is narrow:

> If an application places a synthetic confidential value into model-visible
> system or retrieved/tool-style context, can a user recover it through ordinary
> prompting despite explicit instructions not to reveal it?

This repository does **not** claim provider-hidden prompt leakage,
infrastructure compromise, training-data leakage, or exposure of real user
data. All secrets used here are synthetic canaries.

## What this repository currently proves

The strongest completed evidence in the repo supports an application-visible
confidentiality failure claim, especially for retrieved/tool-style context.

Headline results:

| Setting | Model | Result |
| --- | --- | --- |
| System-context canary replication | `command-r7b-12-2024` | `139/300` exact leaks (`46.4%`) |
| One-shot retrieved/tool-context extraction | `command-r7b-12-2024` | `20/24` exact leaks (`83.3%`) |
| One-shot retrieved/tool-context extraction | `command-r-plus-08-2024` | `18/24` exact leaks (`75.0%`) |
| One-shot retrieved/tool-context extraction | `command-a-03-2025` | `19/24` exact leaks (`79.2%`) |
| Clean two-turn retrieved-context exfiltration | `command-r7b-12-2024` | `15/24` exact leaks (`62.5%`) |
| Clean two-turn retrieved-context exfiltration | `command-r-plus-08-2024` | `1/24` exact leaks (`4.2%`) |
| Clean two-turn retrieved-context exfiltration | `command-a-03-2025` | `0/24` exact leaks (`0.0%`) |
| Repeat-run stability on strongest prompts | `command-r7b-12-2024` | multiple variants reproduced at `19/20` or `20/20` |
| Negative control | `command-r7b-12-2024` | `0/20` exact leaks on `tool-safe-summary` |
| Paired harmful-request baseline | `command-r7b-12-2024` | `0/100` unsafe compliance |

Interpretation:

- harmful-request refusal and confidentiality are separable properties
- retrieved/tool-style context is the most operationally relevant failure mode
- the strongest failures are stable enough to reproduce, not one-off anecdotes
- the narrow claim is about application-supplied sensitive context visible to
  the model

## Repository map

### `paper/`

This directory contains the disclosure package, paper draft, audit artifacts,
and curated evidence summaries.

Most important files:

- `paper/main.tex`
  - current paper draft
- `paper/cohere_submission_packet.md`
  - shortest index of what to send Cohere and in what order
- `paper/cohere_repro_bundle.md`
  - minimal vendor reproduction bundle
- `paper/cohere_vulnerability_list.md`
  - concise findings list
- `paper/cohere_disclosure_draft.md`
  - longer disclosure write-up
- `paper/cohere_email_draft.md`
  - mail-ready disclosure text
- `paper/redteam_repeat_stability_results.md`
  - repeatability evidence for the strongest retrieved-context prompts
- `paper/human_audit_summary.md`
  - manual validation summary
- `paper/human_audit_completed.csv`
  - row-level pilot human audit judgments
- `paper/cohere_model_comparison.md`
  - cross-model comparison
- `paper/redteam_evidence_dossier.md`
  - broader evidence map and artifact index
- `paper/experiment_catalog.md`
  - ranked list of the most important experiments in this repository

### `experiments/`

This directory contains the experiment harnesses and utilities.

Most important scripts:

- `experiments/redteam_tool_context_canary.py`
  - one-shot retrieved/tool-context leakage
- `experiments/redteam_toolchain_exfiltration.py`
  - clean two-turn retrieved-context exfiltration
- `experiments/redteam_canary_rotation.py`
  - multi-canary system-context replication
- `experiments/redteam_multiturn_canary.py`
  - staged multi-turn system-context extraction
- `experiments/redteam_repeat_stability.py`
  - identical reruns on strongest retrieved-context prompts
- `experiments/redteam_behavior.py`
  - broader behavioral harness
- `experiments/score_redteam_responses.py`
  - offline scoring
- `experiments/redteam_confidence_intervals.py`
  - Wilson interval summaries
- `experiments/redteam_proof_bundle.py`
  - redacted representative-case bundle
- `experiments/sample_redteam_audit.py`
  - audit sampling

Supporting docs:

- `experiments/README.md`
  - run instructions and outputs

### `literature/`

Working bibliography and background material.

### `results/`

Local result outputs from completed or dry runs. These are useful operational
artifacts but are not the main curated evidence surface; the `paper/` directory
contains the cleaned summaries intended for review and disclosure.

## Recommended reading order

If you are reviewing this repository for the first time, use this order:

1. `paper/cohere_submission_packet.md`
2. `paper/cohere_repro_bundle.md`
3. `paper/cohere_vulnerability_list.md`
4. `paper/redteam_repeat_stability_results.md`
5. `paper/human_audit_summary.md`
6. `paper/cohere_model_comparison.md`
7. `paper/main.tex`

That order gets a reviewer from claim scope, to reproduction, to evidence
strength, to the longer paper narrative.

## Reproduction paths

### 1. Environment setup

```bash
cd experiments
./setup_env.sh
source .venv/bin/activate
```

Add credentials manually in `experiments/.env` if you plan to run Cohere or
Hugging Face backed experiments.

### 2. Fast defensive smoke test

```bash
python redteam_behavior.py \
  --datasets benign_refusal \
  --n-prompts 5 \
  --difficulty max \
  --out-dir results/redteam_dry_run \
  --dry-run
```

### 3. Highest-value completed experiments

Retrieved/tool-context one-shot extraction:

```bash
python redteam_tool_context_canary.py
```

Clean two-turn retrieved-context exfiltration:

```bash
python redteam_toolchain_exfiltration.py
```

System-context canary rotation:

```bash
python redteam_canary_rotation.py \
  --models command-r7b-12-2024 \
  --n-canaries 5 \
  --n-prompts 60 \
  --out-dir results/redteam_canary_rotation_5x60 \
  --paper-md ../paper/redteam_canary_rotation_results.md \
  --env-path .env \
  --resume
```

Repeat-run stability:

```bash
python redteam_repeat_stability.py \
  --models command-r7b-12-2024 \
  --repeats 20 \
  --out-dir results/redteam_repeat_stability_r7b \
  --paper-md ../paper/redteam_repeat_stability_results.md \
  --env-path .env
```

For a fuller ranked list, see `paper/experiment_catalog.md`.

## Evidence quality controls

This repository tries to do more than collect striking transcripts. The current
evidence package includes:

- multi-canary replication
- cross-model comparison
- repeated identical-rerun stability checks
- negative controls
- count-based confidence intervals
- redacted representative examples with hashed references
- pilot human audit with row-level outcomes

This does **not** make the study complete or final. It does make it more
defensible than an anecdotal prompt dump.

## What to send to Cohere

If the goal is responsible disclosure rather than publication-first review, the
recommended packet is:

- `paper/cohere_submission_packet.md`
- `paper/cohere_repro_bundle.md`
- `paper/cohere_vulnerability_list.md`
- `paper/redteam_repeat_stability_results.md`
- `paper/human_audit_summary.md`

Supporting material:

- `paper/cohere_disclosure_draft.md`
- `paper/cohere_model_comparison.md`
- `paper/redteam_toolchain_statistical_evidence.md`
- `paper/redteam_toolchain_appendix.md`
- `paper/redteam_evidence_dossier.md`

The full paper draft is useful for deeper review, but the vendor packet should
lead because it is faster to parse and easier to reproduce.

## Paper status

The paper draft in `paper/main.tex` is aligned to the completed behavioral
evidence in this repository. It is strongest as a behavioral confidentiality
study and responsible-disclosure record.

One important constraint remains:

- this machine did not have `pdflatex`, so the latest LaTeX edits were improved
  at the source level but not visually PDF-checked here

Compile and inspect the PDF on a LaTeX-capable machine before external
submission.

## Future work

The repository still contains scaffolding for a later open-weight activation
geometry and quantization study. That work is not yet the main claim surface of
this repository and should not be presented as completed until the GPU-backed
runs are done and written up cleanly.

## Claim boundaries

This repository does not support the following claims:

- provider-hidden prompt leakage
- infrastructure compromise
- training-data leakage
- real-user-data exposure
- universal safety failure across all prompt types

The supported claim is narrower:

> Natural-language instructions were not a reliable confidentiality control for
> application-supplied sensitive context visible to the model.

## License and use

Use this repository as a defensive research, disclosure, and documentation
surface. If you publish from it, keep the claim scope narrow and preserve the
difference between exact leakage, partial leakage, and broader transcript-level
effects.
