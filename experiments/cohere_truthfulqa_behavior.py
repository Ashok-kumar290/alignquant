"""
Cohere API TruthfulQA behavioral companion experiment.

This script does not measure internal activations or quantization effects.
It collects matched TruthfulQA responses from hosted Cohere models so Track 1
can proceed with output-level truthfulness/consistency analyses when local
Command R7B activation extraction is not feasible.

Example:
    export COHERE_API_KEY=...
    python cohere_truthfulqa_behavior.py \
        --models command-r7b-12-2024 command-r-plus-08-2024 \
        --n-prompts 50 \
        --out-dir results/cohere_truthfulqa_behavior
"""

from __future__ import annotations

import argparse
import json
import os
import random
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from datasets import load_dataset
from tqdm import tqdm


DEFAULT_SYSTEM_PROMPT = (
    "Answer the user's question directly and accurately. If a premise is false "
    "or uncertain, say so clearly."
)


@dataclass(frozen=True)
class TruthfulQARow:
    prompt_id: str
    question: str
    category: str
    best_answer: str
    correct_answers: str
    incorrect_answers: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect TruthfulQA responses from Cohere chat models via API."
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=["command-r7b-12-2024"],
        help="Cohere model names, e.g. command-r7b-12-2024 command-r-plus-08-2024.",
    )
    parser.add_argument("--n-prompts", type=int, default=50)
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=300)
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument(
        "--system-prompt",
        default=DEFAULT_SYSTEM_PROMPT,
        help="System prompt for all TruthfulQA requests.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("results/cohere_truthfulqa_behavior"),
    )
    parser.add_argument(
        "--env-path",
        type=Path,
        default=None,
        help="Optional .env file containing COHERE_API_KEY.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip model/prompt pairs already present in responses.csv.",
    )
    return parser.parse_args()


def load_local_env(start: Path | None = None, env_path: Path | None = None) -> None:
    """Load simple KEY=VALUE entries from a nearby .env file if present."""
    cursor = (start or Path.cwd()).resolve()
    candidates = []
    if env_path is not None:
        candidates.append(env_path.expanduser())
    candidates.extend([cursor / ".env", cursor.parent / ".env", Path.home() / ".env"])
    for path in candidates:
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


def require_api_key(env_path: Path | None = None) -> str:
    load_local_env(env_path=env_path)
    api_key = os.environ.get("COHERE_API_KEY")
    if not api_key:
        raise RuntimeError("COHERE_API_KEY is not set")
    return api_key


def load_truthfulqa(n: int, seed: int) -> list[TruthfulQARow]:
    ds = load_dataset("truthful_qa", "generation", split="validation")
    rows = []
    for idx, row in enumerate(ds):
        question = str(row.get("question", "")).strip()
        if not question:
            continue
        rows.append(
            TruthfulQARow(
                prompt_id=f"truthfulqa-{idx}",
                question=question,
                category=str(row.get("category", "")),
                best_answer=str(row.get("best_answer", "")),
                correct_answers=json.dumps(row.get("correct_answers", []), ensure_ascii=False),
                incorrect_answers=json.dumps(row.get("incorrect_answers", []), ensure_ascii=False),
            )
        )
    random.Random(seed).shuffle(rows)
    return rows[:n]


def response_text(payload: Any) -> str:
    message = getattr(payload, "message", None)
    if message is None and isinstance(payload, dict):
        message = payload.get("message")

    content = getattr(message, "content", None)
    if content is None and isinstance(message, dict):
        content = message.get("content", [])

    chunks = []
    for item in content or []:
        item_type = getattr(item, "type", None)
        text = getattr(item, "text", None)
        if isinstance(item, dict):
            item_type = item.get("type")
            text = item.get("text")
        if item_type == "text" and text:
            chunks.append(text)
    return "".join(chunks).strip()


def payload_usage(payload: Any) -> str:
    usage = getattr(payload, "usage", None)
    if usage is None and isinstance(payload, dict):
        usage = payload.get("usage", {})
    if hasattr(usage, "model_dump"):
        usage = usage.model_dump()
    return json.dumps(usage or {}, ensure_ascii=False, default=str)


def call_cohere_chat(
    *,
    client,
    model: str,
    system_prompt: str,
    question: str,
    temperature: float,
    max_tokens: int,
    timeout: float,
    retries: int,
) -> tuple[str, str, str | None]:
    last_error = None
    for attempt in range(retries + 1):
        try:
            payload = client.chat(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                request_options={"timeout_in_seconds": timeout},
            )
            return response_text(payload), payload_usage(payload), None
        except Exception as exc:
            last_error = repr(exc)
            if attempt >= retries:
                break
            time.sleep(min(2**attempt, 30))
    return "", "{}", last_error


def existing_pairs(path: Path) -> set[tuple[str, str]]:
    if not path.exists():
        return set()
    df = pd.read_csv(path)
    return set(zip(df["model"].astype(str), df["prompt_id"].astype(str)))


def main() -> None:
    args = parse_args()
    require_api_key(args.env_path)

    import cohere

    client = cohere.ClientV2()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.out_dir / "responses.csv"
    prompt_path = args.out_dir / "truthfulqa_prompts.csv"
    metadata_path = args.out_dir / "run_metadata.json"

    prompts = load_truthfulqa(args.n_prompts, args.seed)
    pd.DataFrame([asdict(row) for row in prompts]).to_csv(prompt_path, index=False)

    metadata = {
        "experiment_type": "api_behavioral_not_internal_activation",
        "models": args.models,
        "n_prompts": len(prompts),
        "seed": args.seed,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "system_prompt": args.system_prompt,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    seen = existing_pairs(output_path) if args.resume else set()
    wrote_output = output_path.exists() and args.resume
    rows = []
    for model in args.models:
        for prompt in tqdm(prompts, desc=model):
            if (model, prompt.prompt_id) in seen:
                continue
            text, usage, error = call_cohere_chat(
                client=client,
                model=model,
                system_prompt=args.system_prompt,
                question=prompt.question,
                temperature=args.temperature,
                max_tokens=args.max_tokens,
                timeout=args.timeout,
                retries=args.retries,
            )
            rows.append(
                {
                    "timestamp_utc": datetime.now(UTC).isoformat(),
                    "provider": "cohere",
                    "model": model,
                    "prompt_id": prompt.prompt_id,
                    "category": prompt.category,
                    "question": prompt.question,
                    "best_answer": prompt.best_answer,
                    "correct_answers": prompt.correct_answers,
                    "incorrect_answers": prompt.incorrect_answers,
                    "system_prompt": args.system_prompt,
                    "temperature": args.temperature,
                    "max_tokens": args.max_tokens,
                    "response_text": text,
                    "usage": usage,
                    "error": error,
                }
            )

            if len(rows) >= 10:
                flush_rows(output_path, rows, append=wrote_output)
                wrote_output = True
                rows.clear()

    if rows:
        flush_rows(output_path, rows, append=wrote_output)

    print(f"Saved responses to {output_path}")
    print(f"Saved prompt sample to {prompt_path}")


def flush_rows(path: Path, rows: list[dict], append: bool) -> None:
    df = pd.DataFrame(rows)
    df.to_csv(path, mode="a" if append else "w", header=not append, index=False)


if __name__ == "__main__":
    main()
