"""Window-aware (causal-safe) feature extraction for triples and encounters.

Two window modes:
  * fraction f of the recorded trajectory (sample-index based),
  * physical time horizon: only samples with t <= t_horizon (the honest
    causal mode used by the v2 experiments).
Features use ONLY window data. The horizon mismatch of the v1 pipeline is
removed: every system (stable or not) uses the same absolute horizon.
"""
from __future__ import annotations

from typing import Any

import numpy as np


# ------------------------------------------------------------------ helpers
def _safe(x: Any) -> np.ndarray:
    return np.nan_to_num(np.asarray(x, dtype=float), nan=0.0, posinf=1e30, neginf=-1e30)


def _slope(y: np.ndarray, t: np.ndarray) -> float:
    if len(y) < 2:
        return 0.0
    try:
        return float(np.polyfit(t, y, 1)[0])
    except Exception:
        return 0.0


def _curv(y: np.ndarray, t: np.ndarray) -> float:
    if len(y) < 3:
        return 0.0
    try:
        return float(2.0 * np.polyfit(t, y, 2)[0])
    except Exception:
        return 0.0


def _spectral_entropy(y: np.ndarray) -> float:
    y = _safe(y)
    if len(y) < 8 or np.allclose(y, y[0]):
        return 0.0
    yc = y - np.mean(y)
    psd = np.abs(np.fft.rfft(yc)) ** 2
    psd = psd[1:]
    tot = psd.sum()
    if tot <= 0:
        return 0.0
    p = psd / tot
    return float(-np.sum(p * np.log(p + 1e-30)) / np.log(len(p)))


def _autocorr(y: np.ndarray, lag: int = 5) -> float:
    y = _safe(y)
    if len(y) <= lag or np.allclose(y, y[0]):
        return 0.0
    yc = y - np.mean(y)
    d = np.dot(yc, yc)
    return float(np.dot(yc[:-lag], yc[lag:]) / d) if d > 0 else 0.0


# ------------------------------------------------------------------ features
def _torque_norms(L_pair: np.ndarray, t: np.ndarray) -> np.ndarray:
    """||Gamma_ij(t)|| = ||dL_ij/dt|| for the three pair channels."""
    Gammas = np.gradient(L_pair, t, axis=0)  # (n,3,3)
    return np.linalg.norm(Gammas, axis=2)    # (n,3)


def extract_window_features(rec: dict, f: float = 1.0, t_horizon: float | None = None,
                            Hcrit: float = 2.5, kappa: float = 4.0) -> np.ndarray:
    """Features from the first fraction f of the recorded trajectory, or from
    samples with t <= t_horizon (physical-time causal window)."""
    t = _safe(rec["t"]); n = len(t)
    if n == 0:
        return np.zeros(len(FEATURE_NAMES))
    if t_horizon is not None:
        nmax = int(np.searchsorted(t, t_horizon, side="right"))
    else:
        nmax = max(2, int(round(n * f)))
    nmax = min(max(nmax, 2), n)
    sl = slice(0, nmax)
    t = t[sl]; H = _safe(rec["H"][sl])
    E = _safe(rec["E_pair"][sl])     # (n,3)
    L = _safe(rec["L_pair"][sl])     # (n,3,3)
    Om = _safe(rec["Omega"][sl])
    dur = t[-1] - t[0]

    dH = np.gradient(H, t)
    d2H = np.gradient(dH, t)
    Hdot_c = max(abs(H[0]) / max(dur, 1e-12), 1e-12)
    psi = 0.5 * (1 + np.tanh(kappa * (np.abs(dH) / Hdot_c - 1)))

    Gnorm = _torque_norms(L, t)      # (n,3)
    Lnorm = np.linalg.norm(L, axis=2)  # (n,3)

    # pairwise-distance features (collision/encounter indicators)
    dp = rec.get("d_pair")
    if dp is None or len(dp) == 0:
        dmin = np.full(nmax, np.nan)
    else:
        dmin = np.min(_safe(dp)[sl], axis=1)
    dmin_min = float(np.nanmin(dmin)) if np.any(np.isfinite(dmin)) else 0.0
    dmin_frac = float(np.nanargmin(dmin) / max(1, nmax - 1)) if np.any(np.isfinite(dmin)) else 1.0
    dmin_rate = np.abs(np.gradient(np.nan_to_num(dmin, nan=1e30), t))
    dmin_rate_max = float(np.max(dmin_rate)) if len(dmin_rate) else 0.0
    # bound-pair identity switches within the window (exchange activity)
    pair_id = np.argmin(E, axis=1)   # most bound pair per sample
    n_pair_changes = int(np.sum(pair_id[1:] != pair_id[:-1])) if n > 1 else 0

    below = H < Hcrit
    crossings = int(np.sum((H[1:] < Hcrit) & (H[:-1] >= Hcrit))) if n > 1 else 0
    breach = np.where(below)[0]
    first_breach = breach[0] / max(1, nmax - 1) if len(breach) else 1.0

    E_std = np.std(E, axis=0)
    E_scale = float(np.mean(np.abs(E)) + 1e-30)
    E_slopes = np.array([_slope(E[:, k], t) for k in range(3)])

    # torque spike ratio (periastron false-positive diagnostic)
    med = np.median(Gnorm, axis=0) + 1e-30
    spike = np.max(Gnorm, axis=0) / med

    feats = np.array([
        # hierarchy stats (12)
        np.min(H), np.max(H), np.mean(H), np.std(H), np.median(H),
        np.max(H) - np.min(H), H[-1], H[0], _slope(H, t), _curv(H, t),
        np.mean(below), crossings,
        # hierarchy derivatives (8)
        np.min(dH), np.max(dH), np.std(dH), np.max(np.abs(dH)),
        np.min(d2H), np.max(d2H), np.std(d2H), np.max(np.abs(d2H)),
        # psi filter (4)
        np.mean(psi), np.max(psi), np.std(psi), psi[-1],
        # pair energies (10)
        E_std[0], E_std[1], E_std[2], E_std.sum(),
        E_std.sum() / E_scale, E_slopes[0], E_slopes[1], E_slopes[2],
        E[-1, 0], E[-1, 1],
        # outer-channel energy (4)
        np.min(_safe(rec["E_out"][sl])), np.max(_safe(rec["E_out"][sl])),
        _safe(rec["E_out"][sl])[-1], _slope(_safe(rec["E_out"][sl]), t),
        # angular momentum channels (12)
        np.min(Lnorm[:, 0]), np.max(Lnorm[:, 0]), np.std(Lnorm[:, 0]),
        np.min(Lnorm[:, 1]), np.max(Lnorm[:, 1]), np.std(Lnorm[:, 1]),
        np.min(Lnorm[:, 2]), np.max(Lnorm[:, 2]), np.std(Lnorm[:, 2]),
        _slope(Lnorm[:, 0], t), _slope(Lnorm[:, 1], t), _slope(Lnorm[:, 2], t),
        # torques (12)
        np.max(Gnorm[:, 0]), np.mean(Gnorm[:, 0]), spike[0],
        np.max(Gnorm[:, 1]), np.mean(Gnorm[:, 1]), spike[1],
        np.max(Gnorm[:, 2]), np.mean(Gnorm[:, 2]), spike[2],
        np.max(Gnorm), np.mean(Gnorm), np.max(spike), np.mean(spike),
        # seam tension (6)
        np.min(Om), np.max(Om), np.mean(Om), np.std(Om), Om[-1], _slope(Om, t),
        # signal processing (3)
        _spectral_entropy(H), _spectral_entropy(Om), _autocorr(H, 5),
        # time anchors (3). Feature slot 73 is permanently deprecated.
        # The former len(window)/len(full_record) definition leaked the future
        # termination length for event-truncated trajectories. Keep a zero
        # placeholder only to preserve the established 79-column schema.
        first_breach, 0.0, dur,
        # pairwise-distance & exchange activity (4)
        dmin_min, dmin_frac, dmin_rate_max, float(n_pair_changes),
    ])
    return np.nan_to_num(feats, nan=0.0, posinf=1e30, neginf=-1e30)


def full_trajectory_features(rec: dict, **kw) -> np.ndarray:
    return extract_window_features(rec, 1.0, **kw)


FEATURE_NAMES = [
    "H_min", "H_max", "H_mean", "H_std", "H_med", "H_range", "H_final", "H_initial",
    "H_slope", "H_curv", "H_below_frac", "H_crossings",
    "dH_min", "dH_max", "dH_std", "abs_dH_max",
    "d2H_min", "d2H_max", "d2H_std", "abs_d2H_max",
    "psi_mean", "psi_max", "psi_std", "psi_final",
    "E01_std", "E02_std", "E12_std", "E_exch", "E_exch_norm",
    "E01_slope", "E02_slope", "E12_slope", "E01_final", "E02_final",
    "Eout_min", "Eout_max", "Eout_final", "Eout_slope",
    "L01_min", "L01_max", "L01_std", "L02_min", "L02_max", "L02_std",
    "L12_min", "L12_max", "L12_std", "L01_slope", "L02_slope", "L12_slope",
    "G01_max", "G01_mean", "G01_spike", "G02_max", "G02_mean", "G02_spike",
    "G12_max", "G12_mean", "G12_spike", "G_all_max", "G_all_mean",
    "G_spike_max", "G_spike_mean",
    "Om_min", "Om_max", "Om_mean", "Om_std", "Om_final", "Om_slope",
    "H_entropy", "Om_entropy", "H_autocorr",
    "first_breach", "n_frac", "dur",
    "dmin_min", "dmin_frac", "dmin_rate_max", "n_pair_changes",
]
