"""
alignquant.quant
Unified loader for FP16 / BnB-int8 / NF4 / GPTQ / AWQ variants of the
same base model. All loaders return (model, tokenizer) ready for the
activation extraction hooks in extract_activations.py.
"""

from __future__ import annotations

from typing import Literal, Tuple

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

QuantScheme = Literal["fp16", "bnb8", "nf4", "gptq", "awq"]


def load_model(
    model_id: str,
    scheme: QuantScheme = "fp16",
    device_map: str = "auto",
) -> Tuple[torch.nn.Module, "AutoTokenizer"]:
    tok = AutoTokenizer.from_pretrained(model_id, use_fast=True)
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token

    if scheme == "fp16":
        model = AutoModelForCausalLM.from_pretrained(
            model_id, torch_dtype=torch.float16, device_map=device_map
        )

    elif scheme == "bnb8":
        cfg = BitsAndBytesConfig(load_in_8bit=True)
        model = AutoModelForCausalLM.from_pretrained(
            model_id, quantization_config=cfg, device_map=device_map
        )

    elif scheme == "nf4":
        cfg = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
        model = AutoModelForCausalLM.from_pretrained(
            model_id, quantization_config=cfg, device_map=device_map
        )

    elif scheme == "gptq":
        # Expect a pre-quantized GPTQ checkpoint on the hub. Transformers
        # auto-detects the GPTQConfig from config.json and dispatches to
        # auto-gptq / optimum for the forward pass. For on-the-fly quantization
        # of an FP16 checkpoint, pass quantization_config=GPTQConfig(bits=4,
        # dataset="c4", tokenizer=tok) instead.
        from transformers import GPTQConfig  # noqa: F401  (kept for reference)

        model = AutoModelForCausalLM.from_pretrained(
            model_id, device_map=device_map, torch_dtype=torch.float16
        )

    elif scheme == "awq":
        # Pre-quantized AWQ checkpoints expose `quantization_config` in their
        # config.json; transformers routes through autoawq automatically.
        # If a raw FP16 id is passed, transformers will load FP16 without
        # quantization — caller is responsible for providing an AWQ checkpoint.
        model = AutoModelForCausalLM.from_pretrained(
            model_id, device_map=device_map, torch_dtype=torch.float16
        )

    else:
        raise ValueError(f"Unknown quant scheme: {scheme}")

    model.eval()
    return model, tok
