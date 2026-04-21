"""
alignquant.extract_activations
Hooks a HuggingFace causal LM and extracts residual-stream activations
at a chosen layer for a batch of prompts. Works identically for FP16,
BnB-int8, NF4, GPTQ, and AWQ loaded models.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import List

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


def decoder_layers(model):
    """Return the decoder block list for common HuggingFace causal LMs."""
    if hasattr(model, "model") and hasattr(model.model, "layers"):
        return model.model.layers
    if hasattr(model, "transformer") and hasattr(model.transformer, "h"):
        return model.transformer.h
    raise AttributeError(
        "Could not locate decoder layers. Add this architecture to decoder_layers()."
    )


@contextmanager
def capture_residual(model, layer_idx: int):
    """Context manager that captures the output of a given decoder layer."""
    captured = {}

    def hook(_module, _inp, out):
        # HF decoder layers return a tuple; [0] is hidden states
        h = out[0] if isinstance(out, tuple) else out
        captured["h"] = h.detach()

    target = decoder_layers(model)[layer_idx]
    handle = target.register_forward_hook(hook)
    try:
        yield captured
    finally:
        handle.remove()


@torch.no_grad()
def last_token_activations(
    model,
    tokenizer,
    prompts: List[str],
    layer_idx: int,
    device: str = "cuda",
    max_length: int = 256,
) -> torch.Tensor:
    """Returns [N, hidden] activations at the last non-pad token of each prompt."""
    acts = []
    for p in prompts:
        toks = tokenizer(p, return_tensors="pt", truncation=True, max_length=max_length).to(device)
        with capture_residual(model, layer_idx) as cap:
            _ = model(**toks)
        h = cap["h"]                     # [1, T, hidden]
        last_idx = toks["attention_mask"].sum(dim=1) - 1
        acts.append(h[0, last_idx.item()].float().cpu())
    return torch.stack(acts, dim=0)
