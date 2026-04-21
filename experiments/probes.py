"""
alignquant.probes
Linear probing + direction extraction for alignment axes.

Three methods implemented (kept deliberately simple / auditable):
  1. diff_in_means      - Arditi et al. 2024 refusal direction
  2. logistic_probe     - classic supervised probe (Azaria-Mitchell / ITI-style)
  3. caa_direction      - Contrastive Activation Addition (Rimsky et al.)

All methods return a unit-norm direction vector per layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

import numpy as np
import torch
import torch.nn.functional as F
from sklearn.linear_model import LogisticRegression


@dataclass
class ProbeResult:
    direction: torch.Tensor          # [hidden_dim], unit-norm
    layer: int
    accuracy: float                  # held-out probe accuracy if applicable
    method: str
    meta: Dict[str, float]


def _unit(v: torch.Tensor, eps: float = 1e-8) -> torch.Tensor:
    return v / (v.norm() + eps)


# ---------------------------------------------------------------------------
# 1. Difference-in-means (Arditi 2024)
# ---------------------------------------------------------------------------

def diff_in_means(
    acts_pos: torch.Tensor,   # [N_pos, hidden]
    acts_neg: torch.Tensor,   # [N_neg, hidden]
    layer: int,
) -> ProbeResult:
    mu_pos = acts_pos.mean(0)
    mu_neg = acts_neg.mean(0)
    d = _unit(mu_pos - mu_neg)

    # simple threshold classifier along d for a quick accuracy number
    proj_pos = acts_pos @ d
    proj_neg = acts_neg @ d
    thr = 0.5 * (proj_pos.mean() + proj_neg.mean())
    acc = (
        (proj_pos > thr).float().mean().item() * 0.5
        + (proj_neg < thr).float().mean().item() * 0.5
    )
    return ProbeResult(
        direction=d.detach().cpu(),
        layer=layer,
        accuracy=float(acc),
        method="diff_in_means",
        meta={"mu_gap": float((mu_pos - mu_neg).norm())},
    )


# ---------------------------------------------------------------------------
# 2. Logistic probe (ITI / Azaria-Mitchell style)
# ---------------------------------------------------------------------------

def logistic_probe(
    acts: torch.Tensor,       # [N, hidden]
    labels: torch.Tensor,     # [N], {0,1}
    layer: int,
    seed: int = 0,
) -> ProbeResult:
    X = acts.float().cpu().numpy()
    y = labels.long().cpu().numpy()
    clf = LogisticRegression(max_iter=2000, C=1.0, random_state=seed).fit(X, y)
    w = torch.tensor(clf.coef_[0], dtype=torch.float32)
    d = _unit(w)
    acc = float(clf.score(X, y))
    return ProbeResult(
        direction=d,
        layer=layer,
        accuracy=acc,
        method="logistic_probe",
        meta={"bias": float(clf.intercept_[0])},
    )


# ---------------------------------------------------------------------------
# 3. CAA (Rimsky et al. 2024)
# ---------------------------------------------------------------------------

def caa_direction(
    acts_a: torch.Tensor,     # behavior-present activations [N, hidden]
    acts_b: torch.Tensor,     # behavior-absent activations  [N, hidden]
    layer: int,
) -> ProbeResult:
    # CAA is essentially paired diff-in-means on matched contrastive pairs
    assert acts_a.shape == acts_b.shape, "CAA expects paired activations"
    d = _unit((acts_a - acts_b).mean(0))
    return ProbeResult(
        direction=d.detach().cpu(),
        layer=layer,
        accuracy=float("nan"),
        method="caa",
        meta={"n_pairs": float(acts_a.shape[0])},
    )


# ---------------------------------------------------------------------------
# Geometry-shift metrics
# ---------------------------------------------------------------------------

def subspace_angle(d_ref: torch.Tensor, d_q: torch.Tensor) -> float:
    """Angle in radians between two unit vectors. Sign-invariant."""
    cs = torch.clamp(torch.abs(torch.dot(_unit(d_ref), _unit(d_q))), 0.0, 1.0)
    return float(torch.arccos(cs))


def cosine_sim(d_ref: torch.Tensor, d_q: torch.Tensor) -> float:
    return float(torch.dot(_unit(d_ref), _unit(d_q)))


def alignquant_score(angles: Sequence[float]) -> float:
    """Aggregate AlignQuant Score: 1 - mean(theta)/(pi/2) in [0,1]."""
    if len(angles) == 0:
        return float("nan")
    return float(1.0 - np.mean(angles) / (np.pi / 2.0))


def random_control_direction(hidden_dim: int, seed: int = 0) -> torch.Tensor:
    g = torch.Generator().manual_seed(seed)
    v = torch.randn(hidden_dim, generator=g)
    return _unit(v)
