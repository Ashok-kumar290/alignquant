"""
AlignQuant - Kaggle Pilot Experiment
=====================================

Minimal end-to-end pilot validating that quantization produces a
measurable subspace angle shift in the refusal direction.

Designed to run on Kaggle free tier (2xT4, 32GB VRAM).

PILOT SCOPE (deliberately small):
    model   : meta-llama/Llama-3-8B-Instruct  (or Mistral-7B-Instruct if gated)
    schemes : FP16 vs NF4
    axis    : refusal direction (Arditi diff-in-means)
    layers  : middle layer (rule of thumb for safety features)
    data    : 64 harmful + 64 harmless prompts from AdvBench/Alpaca

OUTPUT: prints angle(theta_refusal) between FP16 and NF4, plus control
        direction angle. Expected: safety angle >> control angle.

Run:
    pip install -r requirements.txt
    python kaggle_pilot.py
"""

from __future__ import annotations

import gc
import json
from pathlib import Path

import torch

from probes import diff_in_means, subspace_angle
from quant import load_model
from extract_activations import last_token_activations
from data import refusal_pairs

# ------------------------------------------------------------------
# Config
# ------------------------------------------------------------------
MODEL_ID = "mistralai/Mistral-7B-Instruct-v0.3"   # swap to Llama-3-8B if available
LAYER_FRACTION = 0.5                              # middle layer
N_PROMPTS = 128                                   # per class (harmful/harmless)
OUT_DIR = Path("pilot_out")
OUT_DIR.mkdir(exist_ok=True)

HARMFUL, HARMLESS = refusal_pairs(N_PROMPTS)
# Control axis: a semantically-orthogonal binary contrast (poetry vs prose
# instructions). Used as a "random-but-still-a-real-concept" direction so
# that (a) we get an actual activation-extracted direction (not a RNG vector),
# and (b) quantization's effect on any directional structure is controlled for.
# We reuse Alpaca for both halves: split on whether prompt mentions "poem".
def _control_pairs(n: int):
    from data import load_alpaca_harmless
    pool = load_alpaca_harmless(n * 20, seed=7)
    poem = [p for p in pool if "poem" in p.lower() or "poetry" in p.lower()][:n]
    prose = [p for p in pool if "poem" not in p.lower() and "poetry" not in p.lower()][:n]
    # Pad if Alpaca underproduces poems (it will).
    k = min(len(poem), len(prose))
    return poem[:k], prose[:k]

CTRL_A, CTRL_B = _control_pairs(N_PROMPTS)


def get_directions(scheme: str):
    """Return (refusal_dir, control_dir, hidden_dim) for one quant scheme."""
    print(f"\n=== Loading {MODEL_ID} @ {scheme} ===")
    model, tok = load_model(MODEL_ID, scheme=scheme)
    n_layers = model.config.num_hidden_layers
    layer = int(n_layers * LAYER_FRACTION)
    print(f"  hidden layers: {n_layers}, probing layer: {layer}")

    acts_h = last_token_activations(model, tok, HARMFUL, layer_idx=layer)
    acts_s = last_token_activations(model, tok, HARMLESS, layer_idx=layer)
    refusal = diff_in_means(acts_h, acts_s, layer=layer)
    print(f"  refusal probe acc: {refusal.accuracy:.3f}  mu_gap: {refusal.meta['mu_gap']:.3f}")

    acts_a = last_token_activations(model, tok, CTRL_A, layer_idx=layer)
    acts_b = last_token_activations(model, tok, CTRL_B, layer_idx=layer)
    control = diff_in_means(acts_a, acts_b, layer=layer)
    print(f"  control probe acc: {control.accuracy:.3f}  mu_gap: {control.meta['mu_gap']:.3f}")

    hidden_dim = model.config.hidden_size
    del model, tok
    gc.collect()
    torch.cuda.empty_cache()
    return refusal.direction, control.direction, hidden_dim


def main():
    d_ref_fp, d_ctrl_fp, hidden = get_directions("fp16")
    d_ref_q, d_ctrl_q, _ = get_directions("nf4")

    theta_safety = subspace_angle(d_ref_fp, d_ref_q)
    theta_ctrl = subspace_angle(d_ctrl_fp, d_ctrl_q)

    result = {
        "model": MODEL_ID,
        "theta_refusal_rad": theta_safety,
        "theta_refusal_deg": theta_safety * 57.29578,
        "theta_control_rad": theta_ctrl,
        "theta_control_deg": theta_ctrl * 57.29578,
        "signal": theta_safety / max(theta_ctrl, 1e-6),
    }
    print("\n=== PILOT RESULT ===")
    print(json.dumps(result, indent=2))
    (OUT_DIR / "pilot_result.json").write_text(json.dumps(result, indent=2))
    print(f"Saved to {OUT_DIR/'pilot_result.json'}")


if __name__ == "__main__":
    main()
