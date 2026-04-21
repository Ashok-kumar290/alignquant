"""
TruthfulQA FP16 vs 4-bit activation-geometry pilot.

Loads Command R7B twice (FP16 baseline, NF4 4-bit), captures decoder-layer
hidden states for matched TruthfulQA prompts, and writes cosine similarity
metrics for mean activation vectors at selected layers.

Example:
    python truthfulqa_quant_cosine.py \
        --model-id CohereLabs/c4ai-command-r7b-12-2024 \
        --n-prompts 50 \
        --layers 8 16 24 \
        --out-dir results/truthfulqa_r7b_nf4
"""

from __future__ import annotations

import argparse
import gc
import json
import random
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from datasets import load_dataset
from tqdm import tqdm

from extract_activations import capture_residual, decoder_layers
from quant import load_model


@dataclass(frozen=True)
class PromptRecord:
    prompt_id: str
    question: str
    category: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare FP16 and 4-bit Command R7B TruthfulQA activations."
    )
    parser.add_argument(
        "--model-id",
        default="CohereLabs/c4ai-command-r7b-12-2024",
        help="HuggingFace model id for Command R7B or a compatible causal LM.",
    )
    parser.add_argument(
        "--baseline-scheme",
        default="fp16",
        choices=["fp16"],
        help="Reference precision. Kept explicit for reproducibility.",
    )
    parser.add_argument(
        "--quant-scheme",
        default="nf4",
        choices=["nf4", "bnb8"],
        help="BitsAndBytes quantization scheme to compare against FP16.",
    )
    parser.add_argument(
        "--layers",
        nargs="+",
        type=int,
        default=[8, 16, 24],
        help="Zero-indexed decoder layers to hook.",
    )
    parser.add_argument(
        "--n-prompts",
        type=int,
        default=50,
        help="Number of TruthfulQA prompts to evaluate.",
    )
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument(
        "--max-length",
        type=int,
        default=256,
        help="Tokenizer truncation length for each prompt.",
    )
    parser.add_argument(
        "--device",
        default="cuda",
        help="Input tensor device. Use cuda for GPU runs.",
    )
    parser.add_argument(
        "--device-map",
        default="auto",
        help="Transformers device_map argument for model loading.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("results/truthfulqa_quant_cosine"),
        help="Directory for CSV metrics and metadata.",
    )
    parser.add_argument(
        "--save-activations",
        action="store_true",
        help="Also save prompt-level activation matrices as compressed .npz files.",
    )
    parser.add_argument(
        "--no-chat-template",
        action="store_true",
        help="Tokenize raw questions instead of applying the model chat template.",
    )
    parser.add_argument(
        "--dataset-retries",
        type=int,
        default=3,
        help="Retries for loading TruthfulQA from HuggingFace datasets.",
    )
    return parser.parse_args()


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def load_truthfulqa_prompts(n: int, seed: int, retries: int = 3) -> list[PromptRecord]:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            ds = load_dataset("truthful_qa", "generation", split="validation")
            records = [
                PromptRecord(
                    prompt_id=f"truthfulqa-{idx}",
                    question=str(row["question"]).strip(),
                    category=str(row.get("category", "")),
                )
                for idx, row in enumerate(ds)
                if str(row.get("question", "")).strip()
            ]
            rng = random.Random(seed)
            rng.shuffle(records)
            return records[:n]
        except Exception as exc:  # network/cache failures surface from datasets
            last_error = exc
            if attempt < retries:
                time.sleep(2**attempt)
    raise RuntimeError("Failed to load TruthfulQA after retries") from last_error


def validate_layers(model, layers: Iterable[int]) -> list[int]:
    n_layers = len(decoder_layers(model))
    requested = list(layers)
    invalid = [layer for layer in requested if layer < 0 or layer >= n_layers]
    if invalid:
        raise ValueError(f"Invalid layers {invalid}; model has {n_layers} layers indexed 0-{n_layers - 1}")
    return requested


def tokenized_prompt(tokenizer, question: str, max_length: int, use_chat_template: bool):
    if use_chat_template and hasattr(tokenizer, "apply_chat_template"):
        messages = [{"role": "user", "content": question}]
        return tokenizer.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_tensors="pt",
            truncation=True,
            max_length=max_length,
        )
    toks = tokenizer(
        question,
        return_tensors="pt",
        truncation=True,
        max_length=max_length,
    )
    return toks["input_ids"]


@torch.no_grad()
def mean_activations_for_prompts(
    model,
    tokenizer,
    prompts: Sequence[PromptRecord],
    layer_idx: int,
    device: str,
    max_length: int,
    use_chat_template: bool,
) -> torch.Tensor:
    acts: list[torch.Tensor] = []
    model_device = next(model.parameters()).device
    input_device = torch.device(device if torch.cuda.is_available() or device == "cpu" else model_device)

    for record in tqdm(prompts, desc=f"layer {layer_idx}", leave=False):
        input_ids = tokenized_prompt(tokenizer, record.question, max_length, use_chat_template)
        input_ids = input_ids.to(input_device)
        attention_mask = torch.ones_like(input_ids, device=input_ids.device)

        with capture_residual(model, layer_idx) as cap:
            _ = model(input_ids=input_ids, attention_mask=attention_mask, use_cache=False)

        hidden = cap["h"][0].float().cpu()
        seq_len = int(attention_mask[0].sum().item())
        acts.append(hidden[:seq_len].mean(dim=0))

    return torch.stack(acts, dim=0)


def unload_model(model, tokenizer) -> None:
    del model, tokenizer
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def extract_all_layers(
    model_id: str,
    scheme: str,
    layers: Sequence[int],
    prompts: Sequence[PromptRecord],
    args: argparse.Namespace,
) -> dict[int, torch.Tensor]:
    print(f"[load] {model_id} @ {scheme}")
    model, tokenizer = load_model(model_id, scheme=scheme, device_map=args.device_map)
    valid_layers = validate_layers(model, layers)

    outputs: dict[int, torch.Tensor] = {}
    for layer_idx in valid_layers:
        outputs[layer_idx] = mean_activations_for_prompts(
            model=model,
            tokenizer=tokenizer,
            prompts=prompts,
            layer_idx=layer_idx,
            device=args.device,
            max_length=args.max_length,
            use_chat_template=not args.no_chat_template,
        )

    unload_model(model, tokenizer)
    return outputs


def cosine_rows(
    prompts: Sequence[PromptRecord],
    fp16_acts: dict[int, torch.Tensor],
    quant_acts: dict[int, torch.Tensor],
    quant_scheme: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    detail_rows = []
    summary_rows = []

    for layer_idx in sorted(fp16_acts):
        fp = fp16_acts[layer_idx]
        q = quant_acts[layer_idx]
        prompt_cos = F.cosine_similarity(fp, q, dim=1).numpy()

        for record, cosine in zip(prompts, prompt_cos):
            detail_rows.append(
                {
                    "prompt_id": record.prompt_id,
                    "category": record.category,
                    "layer": layer_idx,
                    "quant_scheme": quant_scheme,
                    "cosine_similarity": float(cosine),
                    "question": record.question,
                }
            )

        fp_mean = fp.mean(dim=0)
        q_mean = q.mean(dim=0)
        aggregate_cos = F.cosine_similarity(fp_mean, q_mean, dim=0).item()
        summary_rows.append(
            {
                "layer": layer_idx,
                "quant_scheme": quant_scheme,
                "n_prompts": len(prompts),
                "mean_prompt_cosine": float(np.mean(prompt_cos)),
                "std_prompt_cosine": float(np.std(prompt_cos, ddof=1)) if len(prompt_cos) > 1 else 0.0,
                "min_prompt_cosine": float(np.min(prompt_cos)),
                "max_prompt_cosine": float(np.max(prompt_cos)),
                "aggregate_mean_vector_cosine": float(aggregate_cos),
                "fp16_mean_norm": float(fp_mean.norm().item()),
                "quant_mean_norm": float(q_mean.norm().item()),
            }
        )

    return pd.DataFrame(detail_rows), pd.DataFrame(summary_rows)


def save_activation_snapshots(
    out_dir: Path,
    fp16_acts: dict[int, torch.Tensor],
    quant_acts: dict[int, torch.Tensor],
    quant_scheme: str,
) -> None:
    for label, acts_by_layer in [("fp16", fp16_acts), (quant_scheme, quant_acts)]:
        arrays = {f"layer_{layer}": acts.numpy() for layer, acts in acts_by_layer.items()}
        np.savez_compressed(out_dir / f"truthfulqa_mean_activations_{label}.npz", **arrays)


def main() -> None:
    args = parse_args()
    set_seed(args.seed)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    prompts = load_truthfulqa_prompts(args.n_prompts, args.seed, args.dataset_retries)
    pd.DataFrame([asdict(record) for record in prompts]).to_csv(
        args.out_dir / "truthfulqa_prompts.csv", index=False
    )

    metadata = {
        "model_id": args.model_id,
        "baseline_scheme": args.baseline_scheme,
        "quant_scheme": args.quant_scheme,
        "layers": args.layers,
        "n_prompts": len(prompts),
        "seed": args.seed,
        "max_length": args.max_length,
        "use_chat_template": not args.no_chat_template,
    }
    (args.out_dir / "run_metadata.json").write_text(json.dumps(metadata, indent=2))

    fp16_acts = extract_all_layers(args.model_id, args.baseline_scheme, args.layers, prompts, args)
    quant_acts = extract_all_layers(args.model_id, args.quant_scheme, args.layers, prompts, args)

    detail_df, summary_df = cosine_rows(prompts, fp16_acts, quant_acts, args.quant_scheme)
    detail_df.to_csv(args.out_dir / "per_prompt_layer_cosine.csv", index=False)
    summary_df.to_csv(args.out_dir / "layer_summary.csv", index=False)

    if args.save_activations:
        save_activation_snapshots(args.out_dir, fp16_acts, quant_acts, args.quant_scheme)

    print("\n=== Layer summary ===")
    print(summary_df.to_string(index=False))
    print(f"\nSaved outputs to {args.out_dir}")


if __name__ == "__main__":
    main()
