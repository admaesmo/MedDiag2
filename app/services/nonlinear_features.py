"""Deterministic nonlinear voice feature extraction (base version).

Implements practical approximations for:
- DFA (Detrended Fluctuation Analysis)
- D2 (Correlation Dimension via Grassberger-Procaccia style estimator)
- PPE (Pitch Period Entropy)
"""

from __future__ import annotations

from typing import Dict

import numpy as np


class NonlinearFeatureError(Exception):
    """Raised when nonlinear features cannot be computed."""


def _safe_log_space(min_n: int, max_n: int, count: int) -> np.ndarray:
    vals = np.unique(np.logspace(np.log10(min_n), np.log10(max_n), num=count).astype(int))
    return vals[vals > 1]


def compute_dfa(signal: np.ndarray) -> float:
    x = np.asarray(signal, dtype=np.float64)
    x = x[np.isfinite(x)]
    if x.size < 128:
        raise NonlinearFeatureError("Not enough samples for DFA")

    x = x - np.mean(x)
    y = np.cumsum(x)

    min_window = 8
    max_window = max(min_window + 1, x.size // 4)
    windows = _safe_log_space(min_window, max_window, count=16)

    flucts = []
    valid_windows = []

    for w in windows:
        n_segments = x.size // w
        if n_segments < 4:
            continue

        y_cut = y[: n_segments * w].reshape(n_segments, w)
        t = np.arange(w)

        rms_vals = []
        for seg in y_cut:
            coeff = np.polyfit(t, seg, 1)
            trend = coeff[0] * t + coeff[1]
            detrended = seg - trend
            rms_vals.append(np.sqrt(np.mean(detrended ** 2)))

        f_w = float(np.sqrt(np.mean(np.square(rms_vals))))
        if np.isfinite(f_w) and f_w > 0:
            flucts.append(f_w)
            valid_windows.append(w)

    if len(flucts) < 4:
        raise NonlinearFeatureError("Insufficient window scales for DFA")

    slope, _ = np.polyfit(np.log(valid_windows), np.log(flucts), 1)
    return float(slope)


def _embed(signal: np.ndarray, m: int, tau: int) -> np.ndarray:
    n = signal.size - (m - 1) * tau
    if n <= 0:
        return np.empty((0, m), dtype=np.float64)

    out = np.empty((n, m), dtype=np.float64)
    for i in range(m):
        out[:, i] = signal[i * tau : i * tau + n]
    return out


def compute_d2(signal: np.ndarray, m: int = 3, tau: int = 2) -> float:
    x = np.asarray(signal, dtype=np.float64)
    x = x[np.isfinite(x)]
    if x.size < 400:
        raise NonlinearFeatureError("Not enough samples for D2")

    z = (x - np.mean(x)) / (np.std(x) + 1e-12)
    emb = _embed(z, m=m, tau=tau)
    if emb.shape[0] < 120:
        raise NonlinearFeatureError("Insufficient embedded points for D2")

    # Subsample for manageable O(n^2) computation.
    max_points = 350
    if emb.shape[0] > max_points:
        idx = np.linspace(0, emb.shape[0] - 1, max_points).astype(int)
        emb = emb[idx]

    diff = emb[:, None, :] - emb[None, :, :]
    dist = np.sqrt(np.sum(diff * diff, axis=2))

    iu = np.triu_indices(dist.shape[0], k=1)
    d = dist[iu]
    d = d[np.isfinite(d) & (d > 0)]
    if d.size < 200:
        raise NonlinearFeatureError("Insufficient distance pairs for D2")

    r_min = np.percentile(d, 5)
    r_max = np.percentile(d, 35)
    if not np.isfinite(r_min) or not np.isfinite(r_max) or r_max <= r_min:
        raise NonlinearFeatureError("Invalid radius range for D2")

    radii = np.logspace(np.log10(r_min), np.log10(r_max), num=14)
    c_vals = []
    r_vals = []

    for r in radii:
        c_r = np.mean(d < r)
        if c_r > 0:
            c_vals.append(c_r)
            r_vals.append(r)

    if len(c_vals) < 5:
        raise NonlinearFeatureError("Insufficient correlation sum samples for D2")

    slope, _ = np.polyfit(np.log(r_vals), np.log(c_vals), 1)
    return float(slope)


def compute_ppe(f0: np.ndarray) -> float:
    pitch = np.asarray(f0, dtype=np.float64)
    pitch = pitch[np.isfinite(pitch) & (pitch > 0)]
    if pitch.size < 20:
        raise NonlinearFeatureError("Not enough voiced pitch points for PPE")

    log_pitch = np.log(pitch)
    centered = log_pitch - np.mean(log_pitch)

    hist, _ = np.histogram(centered, bins=30, density=True)
    p = hist / (np.sum(hist) + 1e-12)
    p = p[p > 0]

    entropy = -np.sum(p * np.log(p))
    max_entropy = np.log(30)
    if max_entropy <= 0:
        raise NonlinearFeatureError("Invalid entropy normalization")

    return float(entropy / max_entropy)


def compute_nonlinear_features(y: np.ndarray, f0: np.ndarray) -> Dict[str, float]:
    """Return deterministic nonlinear feature subset for current iteration."""

    features: Dict[str, float] = {}

    try:
        features["DFA"] = compute_dfa(y)
    except Exception:
        features["DFA"] = 0.0

    try:
        features["D2"] = compute_d2(y)
    except Exception:
        features["D2"] = 0.0

    try:
        features["PPE"] = compute_ppe(f0)
    except Exception:
        features["PPE"] = 0.0

    # Keep compatibility with existing full feature schema.
    if "spread1" not in features:
        features["spread1"] = 0.0
    if "spread2" not in features:
        features["spread2"] = 0.0
    if "RPDE" not in features:
        features["RPDE"] = 0.0

    return features
