"""Extracción determinística de biomarcadores no lineales de voz.
Implementa aproximaciones prácticas para:
- DFA (análisis de fluctuaciones sin tendencia)
- D2 (dimensión de correlación con estimador tipo Grassberger-Procaccia)
- PPE (entropía de periodo de pitch)
- RPDE (entropía de densidad de periodos recurrentes)
- spread1/spread2 (descriptores distribucionales sobre log-pitch)
"""

from __future__ import annotations

import logging
from typing import Dict

import numpy as np

logger = logging.getLogger(__name__)


class NonlinearFeatureError(Exception):
    """Se lanza cuando los biomarcadores no lineales no pueden calcularse."""


def _safe_log_space(min_n: int, max_n: int, count: int) -> np.ndarray:
    vals = np.unique(np.logspace(np.log10(min_n), np.log10(max_n), num=count).astype(int))
    return vals[vals > 1]


def compute_dfa(signal: np.ndarray) -> float:
    x = np.asarray(signal, dtype=np.float64)
    x = x[np.isfinite(x)]
    if x.size < 128:
        raise NonlinearFeatureError("No hay suficientes muestras para DFA")

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
        t = np.arange(w, dtype=np.float64)

        # Regresión lineal por segmento vectorizada (forma cerrada de OLS),
        # equivalente a llamar np.polyfit(t, seg, 1) por fila pero sin el
        # loop de Python — con ventanas pequeñas hay miles de segmentos y
        # el loop por-fila dominaba el tiempo de extracción (~2.5s de los
        # ~2.6s de todas las features no lineales en un audio de 6s).
        t_mean = t.mean()
        t_centered = t - t_mean
        denom = np.sum(t_centered ** 2)
        y_mean = y_cut.mean(axis=1)
        slope = (y_cut @ t_centered) / denom
        intercept = y_mean - slope * t_mean
        trend = slope[:, None] * t[None, :] + intercept[:, None]
        detrended = y_cut - trend
        rms_vals = np.sqrt(np.mean(detrended ** 2, axis=1))

        f_w = float(np.sqrt(np.mean(np.square(rms_vals))))
        if np.isfinite(f_w) and f_w > 0:
            flucts.append(f_w)
            valid_windows.append(w)

    if len(flucts) < 4:
        raise NonlinearFeatureError("Escalas de ventana insuficientes para DFA")

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
        raise NonlinearFeatureError("No hay suficientes muestras para D2")

    z = (x - np.mean(x)) / (np.std(x) + 1e-12)
    emb = _embed(z, m=m, tau=tau)
    if emb.shape[0] < 120:
        raise NonlinearFeatureError("Puntos embebidos insuficientes para D2")

    # Submuestrea para mantener manejable el cálculo O(n^2).
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
        raise NonlinearFeatureError("Pares de distancia insuficientes para D2")

    r_min = np.percentile(d, 5)
    r_max = np.percentile(d, 35)
    if not np.isfinite(r_min) or not np.isfinite(r_max) or r_max <= r_min:
        raise NonlinearFeatureError("Rango de radio inválido para D2")

    radii = np.logspace(np.log10(r_min), np.log10(r_max), num=14)
    c_vals = []
    r_vals = []

    for r in radii:
        c_r = np.mean(d < r)
        if c_r > 0:
            c_vals.append(c_r)
            r_vals.append(r)

    if len(c_vals) < 5:
        raise NonlinearFeatureError("Muestras insuficientes de suma de correlación para D2")

    slope, _ = np.polyfit(np.log(r_vals), np.log(c_vals), 1)
    return float(slope)


def compute_ppe(f0: np.ndarray) -> float:
    pitch = np.asarray(f0, dtype=np.float64)
    pitch = pitch[np.isfinite(pitch) & (pitch > 0)]
    if pitch.size < 20:
        raise NonlinearFeatureError("No hay suficientes puntos de pitch sonoro para PPE")

    log_pitch = np.log(pitch)
    centered = log_pitch - np.mean(log_pitch)

    hist, _ = np.histogram(centered, bins=30, density=True)
    p = hist / (np.sum(hist) + 1e-12)
    p = p[p > 0]

    entropy = -np.sum(p * np.log(p))
    max_entropy = np.log(30)
    if max_entropy <= 0:
        raise NonlinearFeatureError("Normalización de entropía inválida")

    return float(entropy / max_entropy)


def compute_rpde(f0: np.ndarray, max_lag: int = 120) -> float:
    """
    Aproxima RPDE desde los rezagos de recurrencia del periodo de pitch.

    Usa la distribución de rezagos de primer retorno sobre la secuencia
    normalizada de periodos. La salida es entropía normalizada en [0, 1]
    cuando es posible.
    """
    pitch = np.asarray(f0, dtype=np.float64)
    pitch = pitch[np.isfinite(pitch) & (pitch > 0)]
    if pitch.size < 30:
        raise NonlinearFeatureError("No hay suficientes puntos de pitch sonoro para RPDE")

    periods = 1.0 / pitch
    periods = (periods - np.mean(periods)) / (np.std(periods) + 1e-12)

    eps = 0.2
    lags = []
    n = periods.size

    for i in range(n - 2):
        upper = min(n, i + max_lag + 1)
        found = False
        for j in range(i + 1, upper):
            if abs(periods[j] - periods[i]) <= eps:
                lags.append(j - i)
                found = True
                break
        if not found:
            continue

    if len(lags) < 15:
        raise NonlinearFeatureError("Rezagos de recurrencia insuficientes para RPDE")

    hist, _ = np.histogram(lags, bins=np.arange(1, max_lag + 2), density=False)
    p = hist.astype(np.float64)
    p = p / (np.sum(p) + 1e-12)
    p = p[p > 0]

    entropy = -np.sum(p * np.log(p))
    max_entropy = np.log(max_lag)
    if max_entropy <= 0:
        raise NonlinearFeatureError("Normalización RPDE inválida")

    return float(entropy / max_entropy)


def compute_spread_features(f0: np.ndarray) -> Dict[str, float]:
    """
    Aproxima spread1/spread2 desde la distribución de log-pitch.

    spread1: desplazamiento de la cola inferior respecto a la mediana
    (típicamente negativo).
    spread2: dispersión robusta sobre log-pitch centrado (positiva).
    """
    pitch = np.asarray(f0, dtype=np.float64)
    pitch = pitch[np.isfinite(pitch) & (pitch > 0)]
    if pitch.size < 20:
        raise NonlinearFeatureError(
            "No hay suficientes puntos de pitch sonoro para las características spread"
        )

    lp = np.log(pitch)
    centered = lp - np.median(lp)

    p10 = np.percentile(centered, 10)
    p90 = np.percentile(centered, 90)
    iqr = np.percentile(centered, 75) - np.percentile(centered, 25)

    spread1 = float(p10)
    spread2 = float(0.5 * (p90 - p10) + 0.5 * iqr)
    return {"spread1": spread1, "spread2": spread2}


def compute_nonlinear_features(
    y: np.ndarray, f0: np.ndarray
) -> tuple[Dict[str, float], list[str]]:
    """
    Calcula biomarcadores no lineales y reporta explícitamente los que fallaron.

    Retorna
    -------
    features : Dict[str, float]
        Biomarcadores calculados con éxito.
    missing : list[str]
        Nombres de los biomarcadores que no pudieron calcularse.
    """
    features: Dict[str, float] = {}
    missing: list[str] = []

    try:
        features["DFA"] = compute_dfa(y)
    except Exception as exc:
        logger.debug("compute_dfa falló: %s", exc)
        missing.append("DFA")

    try:
        features["D2"] = compute_d2(y)
    except Exception as exc:
        logger.debug("compute_d2 falló: %s", exc)
        missing.append("D2")

    try:
        features["PPE"] = compute_ppe(f0)
    except Exception as exc:
        logger.debug("compute_ppe falló: %s", exc)
        missing.append("PPE")

    try:
        features["RPDE"] = compute_rpde(f0)
    except Exception as exc:
        logger.debug("compute_rpde falló: %s", exc)
        missing.append("RPDE")

    try:
        features.update(compute_spread_features(f0))
    except Exception as exc:
        logger.debug("compute_spread_features falló: %s", exc)
        missing.extend(["spread1", "spread2"])

    return features, missing
