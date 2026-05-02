# AlignQuant Experiment Catalog

This document lists the highest-value experiments in this repository, what each
one proves, when to run it, and where its outputs land. It is meant to be the
single index for red-teaming, disclosure support, and the later open-weight
quantization study.

## 1. Recommended order

| Priority | Experiment | Why it matters | Current value |
| --- | --- | --- | --- |
| 1 | Retrieved-context single-turn leakage | Strongest practical failure signal across models | High |
| 2 | Clean two-turn tool-chain exfiltration | Closest to a realistic RAG / agent failure | High |
| 3 | System-context canary rotation | Strong replication evidence against one-off artifacts | High |
| 4 | System-context multi-turn extraction | Shows staged conversational leakage pressure | High |
| 5 | Broad behavioral red-team harness | Baseline refusal / safety context around the leakage findings | Medium |
| 6 | Repeat-run stability on top prompts | Shows whether the strongest failures persist across repeated identical runs | High |
| 7 | Human-audit sampling and proof bundle | Vendor-facing evidence and paper appendix support | High |
| 8 | TruthfulQA activation geometry pilot | Future open-weight quantization/mechanistic work | Medium, blocked by GPU |

## 2. Headline experiments

### 2.1 Retrieved-context single-turn leakage

**Script**
- `experiments/redteam_tool_context_canary.py`

**Purpose**
- Tests whether models reveal a synthetic confidential field when it appears in
  retrieved/tool-style context.
- This is the most direct proxy for real retrieval-augmented generation and
  agent setups where internal records are passed to the model.

**Why it is effective**
- It is practical, simple, and strong.
- In this repository, it produced heavy exact leakage across all three tested
  Cohere models.

**Run**
```bash
cd /home/ubuntu/alignquant/experiments
source .venv/bin/activate
python redteam_tool_context_canary.py
```

**Primary output**
- `paper/redteam_tool_context_canary_results.md`

**Best use**
- First vendor-facing demonstration of application-visible confidential-context
  leakage in a realistic setting.

### 2.2 Clean two-turn tool-chain exfiltration

**Script**
- `experiments/redteam_toolchain_exfiltration.py`

**Purpose**
- Simulates a safer-looking two-step workflow:
  1. the model receives a confidential retrieved record,
  2. the first turn asks only for a safe summary or redacted view,
  3. the second turn asks for the exact confidential token.

**Why it is effective**
- This is the strongest staged exfiltration experiment in the repo.
- It is closer to production workflows than one-shot system-prompt extraction.

**Run**
```bash
cd /home/ubuntu/alignquant/experiments
source .venv/bin/activate
python redteam_toolchain_exfiltration.py
```

**Primary outputs**
- `paper/redteam_toolchain_exfiltration_clean_results.md`
- `paper/redteam_toolchain_statistical_evidence.md`
- `paper/redteam_toolchain_appendix.md`

**Best use**
- Strongest reportable behavioral evidence for Cohere.
- Strongest paper-grade evidence for staged confidentiality failure.

### 2.3 System-context canary rotation

**Script**
- `experiments/redteam_canary_rotation.py`

**Purpose**
- Repeats the same system-context leakage test with multiple independent
  synthetic canaries.

**Why it is effective**
- It shows whether leakage survives token changes.
- It directly answers the objection that the result may be tied to one string.

**Run**
```bash
cd /home/ubuntu/alignquant/experiments
source .venv/bin/activate
python redteam_canary_rotation.py \
  --models command-r7b-12-2024 \
  --n-canaries 5 \
  --n-prompts 60 \
  --out-dir results/redteam_canary_rotation_5x60 \
  --paper-md ../paper/redteam_canary_rotation_results.md \
  --env-path .env \
  --resume
```

**Primary outputs**
- `paper/redteam_canary_rotation_results.md`
- `paper/redteam_statistical_evidence.md`

**Best use**
- Replication and statistical-strength evidence.

### 2.4 System-context multi-turn extraction

**Script**
- `experiments/redteam_multiturn_canary.py`

**Purpose**
- Tests whether staged conversations recover a hidden canary more reliably than
  one-shot prompts.

**Why it is effective**
- It surfaces hierarchy, quoting, transformation, and roleplay weaknesses that
  do not always appear in the first turn.

**Run**
```bash
cd /home/ubuntu/alignquant/experiments
source .venv/bin/activate
python redteam_multiturn_canary.py \
  --models command-r7b-12-2024 \
  --n-canaries 5 \
  --out-dir results/redteam_multiturn_canary_5x10 \
  --paper-md ../paper/redteam_multiturn_canary_results.md \
  --env-path .env
```

**Primary outputs**
- `paper/redteam_multiturn_canary_results.md`
- `paper/redteam_multiturn_canary_multimodel_results.md`

**Best use**
- Demonstrates that apparently safe first turns do not guarantee later
  confidentiality.

## 3. Core support experiments and utilities

### 3.1 Repeat-run stability on top prompts

**Script**
- `experiments/redteam_repeat_stability.py`

**Purpose**
- Repeats the strongest retrieved-context prompts against the same model to
  distinguish stable failure modes from one-off artifacts.
- Includes both top leak probes and negative controls.

**Best use**
- Minimal vendor reproduction and stability evidence.

### 3.2 Broad behavioral red-team harness

**Script**
- `experiments/redteam_behavior.py`

**Purpose**
- General harness for harmful prompts, benign refusal, truthfulness,
  confidential-context leakage, hierarchy confusion, and boundary probes.

**Run examples**
```bash
python redteam_behavior.py \
  --provider cohere \
  --models command-r7b-12-2024 \
  --datasets advbench benign_refusal truthfulqa \
  --difficulty max \
  --n-prompts 100 \
  --out-dir results/redteam_behavior_max_100
```

```bash
python redteam_behavior.py \
  --provider cohere \
  --models command-r7b-12-2024 \
  --datasets canary_leak hierarchy_attack boundary_probe \
  --difficulty max \
  --n-prompts 100 \
  --out-dir results/redteam_deep_max_100
```

**Best use**
- Provides the baseline safety story around the narrower leakage findings.

### 3.3 Offline scoring

**Script**
- `experiments/score_redteam_responses.py`

**Purpose**
- Scores exact, normalized, partial, and encoded leakage plus refusal-related
  behaviors.

**Best use**
- Required for consistent cross-run summaries and later confidence intervals.

### 3.4 Confidence intervals

**Script**
- `experiments/redteam_confidence_intervals.py`

**Purpose**
- Converts raw score files into count-based Wilson interval summaries.

**Best use**
- Turns a pilot into statistically legible evidence.

### 3.5 Vendor proof bundle

**Script**
- `experiments/redteam_proof_bundle.py`

**Purpose**
- Builds a redacted set of representative cases with raw-record hashes.

**Best use**
- Vendor reporting and evidence appendix.

### 3.6 Human audit sampling

**Script**
- `experiments/sample_redteam_audit.py`

**Purpose**
- Pulls a balanced audit sample from scored outputs for manual review.

**Best use**
- Reduces overreliance on rule-based scoring.

### 3.7 Summary table generation

**Script**
- `experiments/generate_redteam_tables.py`

**Purpose**
- Generates compact summary tables from completed runs.

**Best use**
- Fast paper/report table refresh after new runs.

## 4. Future open-weight quantization experiments

### 4.1 TruthfulQA activation geometry pilot

**Scripts**
- `experiments/truthfulqa_quant_cosine.py`
- `experiments/truthfulqa_activation_report.py`

**Purpose**
- Measures FP16 vs quantized activation geometry drift on an open-weight model.
- This is the bridge from the current behavioral paper to the intended
  quantization/mechanistic story.

**Run**
```bash
cd /home/ubuntu/alignquant/experiments
source .venv/bin/activate
python truthfulqa_quant_cosine.py \
  --model-id Qwen/Qwen2.5-1.5B-Instruct \
  --n-prompts 50 \
  --layers 8 16 24 \
  --quant-scheme nf4 \
  --out-dir results/truthfulqa_qwen25_15b_nf4

python truthfulqa_activation_report.py \
  --run-dir results/truthfulqa_qwen25_15b_nf4 \
  --out-md ../paper/truthfulqa_qwen25_15b_nf4_report.md
```

**Current constraint**
- Not feasible on the current EC2 instance because there is no usable GPU and
  RAM is too limited for a meaningful run.

**Best use**
- First credible open-weight geometry slice once GPU access is available.

## 5. Evidence map

| Experiment | Primary paper/report artifact |
| --- | --- |
| Retrieved-context single-turn leakage | `paper/redteam_tool_context_canary_results.md` |
| Clean two-turn tool-chain exfiltration | `paper/redteam_toolchain_exfiltration_clean_results.md` |
| Repeat-run stability | `paper/redteam_repeat_stability_results.md` |
| Tool-chain confidence intervals | `paper/redteam_toolchain_statistical_evidence.md` |
| Tool-chain appendix | `paper/redteam_toolchain_appendix.md` |
| System-context canary rotation | `paper/redteam_canary_rotation_results.md` |
| System-context multi-turn extraction | `paper/redteam_multiturn_canary_results.md` |
| Cross-model comparison | `paper/cohere_model_comparison.md` |
| Vendor disclosure draft | `paper/cohere_disclosure_draft.md` |
| Vendor submission packet | `paper/cohere_submission_packet.md` |
| Vendor repro bundle | `paper/cohere_repro_bundle.md` |
| Vendor vulnerability list | `paper/cohere_vulnerability_list.md` |
| Human audit protocol | `paper/human_audit_protocol.md` |
| Human audit template CSV | `paper/human_audit_completed_template.csv` |
| Human audit completed CSV | `paper/human_audit_completed.csv` |
| Human audit summary | `paper/human_audit_summary.md` |
| Consolidated evidence dossier | `paper/redteam_evidence_dossier.md` |
| Current paper draft | `paper/main.tex` |

## 6. Practical guidance

If the goal is **vendor disclosure**, run and lead with:
1. retrieved-context single-turn leakage,
2. clean two-turn tool-chain exfiltration,
3. system-context canary rotation,
4. confidence intervals plus proof bundle.

If the goal is **paper quality**, add:
1. human-audit sampling,
2. cross-model comparison,
3. one open-weight activation geometry pilot once GPU access exists.

If the goal is **fast local validation**, run:
1. `redteam_behavior.py --dry-run`
2. the scoring pipeline
3. table generation

## 7. Current strongest evidence

The most effective completed experiments in this repository are:

1. **Retrieved-context single-turn leakage**  
   Strong practical leakage across all three tested Cohere models.

2. **Clean two-turn tool-chain exfiltration**  
   Strong staged exfiltration on `command-r7b-12-2024`, weaker but still useful
   comparative results on the stronger models.

3. **Five-canary system-context replication**  
   Strong replication evidence that the leakage is not a one-token artifact.

These three experiments are the core of the current disclosure and paper story.
