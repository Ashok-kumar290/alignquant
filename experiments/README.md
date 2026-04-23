# AlignQuant Experiments

## Quick start
```bash
cd experiments
./setup_env.sh
source .venv/bin/activate
```

## Structure (to build)
- `probes/` — linear probe training & evaluation
- `quant/` — unified quantization wrappers (BnB8, NF4, GPTQ, AWQ)
- `metrics/` — geometry-shift metrics, AlignQuant Score
- `data/` — TruthfulQA, BeaverTails, SycEval, etc. loaders
- `pipelines/` — end-to-end experiment scripts
- `configs/` — YAML configs for model × quant × axis sweeps

## Pilot plan (Phase C5)
Model: LLaMA-2-7B-chat
Axis: TruthfulQA truthfulness probe
Quant: FP16 baseline vs 4-bit NF4
Goal: validate measurable geometry shift before scaling.

## Local activation pilot

Use a small open-weight model on local hardware to validate the activation
geometry pipeline before moving to Command R7B on a larger GPU runtime:
```bash
python truthfulqa_quant_cosine.py \
  --model-id Qwen/Qwen2.5-1.5B-Instruct \
  --n-prompts 50 \
  --layers 8 16 24 \
  --quant-scheme nf4 \
  --out-dir results/truthfulqa_qwen25_15b_nf4
```

This is the right first run on a 16GB single-GPU machine. It measures internal
activation shifts under FP16 vs NF4 4-bit quantization, but it is not a Cohere
model result.

## Command R7B activation pilot
```bash
python truthfulqa_quant_cosine.py \
  --model-id CohereLabs/c4ai-command-r7b-12-2024 \
  --n-prompts 50 \
  --layers 8 16 24 \
  --quant-scheme nf4 \
  --out-dir results/truthfulqa_r7b_nf4
```

Outputs:
- `truthfulqa_prompts.csv` — sampled prompt IDs, categories, and questions.
- `per_prompt_layer_cosine.csv` — paired FP16 vs quantized cosine per prompt and layer.
- `layer_summary.csv` — mean/std/min/max prompt cosine and aggregate mean-vector cosine per layer.
- `run_metadata.json` — model, seed, layers, prompt count, and tokenization settings.

Use `--save-activations` to additionally save compressed prompt-level mean activation matrices.

This requires enough GPU memory to load Command R7B in FP16 for the baseline.
If the local machine cannot load it, run the local activation pilot above and
use the API companion below for Cohere-specific behavioral data.

## Cohere API TruthfulQA behavioral companion
```bash
export COHERE_API_KEY=...
python cohere_truthfulqa_behavior.py \
  --models command-r7b-12-2024 command-r-plus-08-2024 command-a-03-2025 \
  --n-prompts 50 \
  --out-dir results/cohere_truthfulqa_behavior
```

Outputs:
- `truthfulqa_prompts.csv` — sampled prompt IDs, categories, reference answers, and questions.
- `responses.csv` — Cohere API responses and usage/error metadata.
- `run_metadata.json` — model list, seed, decoding settings, and system prompt.

This is an output-level behavioral experiment only. Hosted API responses do not
expose transformer layer activations or selectable FP16/NF4 precision, so do
not report these results as internal activation geometry or quantization data.

## Behavioral red-team harness
```bash
export COHERE_API_KEY=...
python redteam_behavior.py \
  --provider cohere \
  --models command-r7b-12-2024 \
  --datasets advbench benign_refusal truthfulqa \
  --difficulty baseline \
  --n-prompts 50 \
  --out-dir results/redteam_behavior
```

Harder defensive red-team run:
```bash
python redteam_behavior.py \
  --provider cohere \
  --models command-r7b-12-2024 \
  --datasets advbench benign_refusal truthfulqa \
  --difficulty max \
  --n-prompts 100 \
  --out-dir results/redteam_behavior_max_100
```

Deep vulnerability probes for confidential-context leakage, instruction
hierarchy confusion, and safe-boundary over-refusal:
```bash
python redteam_behavior.py \
  --provider cohere \
  --models command-r7b-12-2024 \
  --datasets canary_leak hierarchy_attack boundary_probe \
  --difficulty max \
  --n-prompts 100 \
  --out-dir results/redteam_deep_max_100
```

Offline rescoring for exact, normalized, partial, and encoded canary leakage:
```bash
python score_redteam_responses.py \
  --run-dir results/redteam_deep_max_100
```

Redacted human-audit sampling from rescored outputs:
```bash
python sample_redteam_audit.py \
  --run-dir results/redteam_deep_max_100 \
  --out-prefix audit_sample \
  --per-label 8
```

Generate compact headline tables from completed summaries:
```bash
python generate_redteam_tables.py \
  --baseline-run results/redteam_behavior_max_100 \
  --deep-run results/redteam_deep_max_100 \
  --out-dir results/redteam_tables
```

To validate local wiring without credentials or network-heavy datasets:
```bash
python redteam_behavior.py \
  --datasets benign_refusal \
  --n-prompts 5 \
  --difficulty max \
  --out-dir results/redteam_dry_run \
  --dry-run
```

Outputs:
- `prompts.csv` — sampled prompt cases with dataset, category, risk type, and reference fields.
- `responses.csv` — provider/model responses and request metadata.
- `scores.csv` — conservative rule-based labels for refusal, unsafe compliance, over-refusal, and uncertainty acknowledgement.
- `summary.json` — model × dataset aggregate rates.
- `run_metadata.json` — provider, model list, datasets, decoding settings, and scorer version.

This harness is designed for defensive evaluation. It is intentionally behavioral
and conservative; use it to compare output-level safety before later joining the
same prompt IDs with activation-geometry experiments.
