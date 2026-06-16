"""
Validador de calidad de features extraídas de audio.

Detecta valores aberrantes comparando con los rangos conocidos del
dataset UCI Oxford con el que fue entrenado el modelo de Parkinson.

Si demasiadas features están fuera de rango, la extracción de audio
falló y no se debe confiar en la predicción.

Incluye una función de saneamiento (``sanitize_features``) que ajusta
valores fuera de rango a los límites del dataset UCI, como solución
temporal para lidiar con grabaciones ruidosas o de baja calidad.
"""

from __future__ import annotations

import copy
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

# Rangos del dataset UCI Oxford (parkinsons.data)
# Formato: {feature_name: (min, max)}
UCI_RANGES: Dict[str, Tuple[float, float]] = {
    "MDVP:Fo(Hz)":       (88.0, 260.0),
    "MDVP:Fhi(Hz)":      (100.0, 600.0),
    "MDVP:Flo(Hz)":      (65.0, 240.0),
    "MDVP:Jitter(%)":    (0.001, 0.033),
    "MDVP:Jitter(Abs)":  (0.000007, 0.00026),
    "MDVP:RAP":          (0.0005, 0.021),
    "MDVP:PPQ":          (0.0005, 0.02),
    "Jitter:DDP":        (0.0015, 0.063),
    "MDVP:Shimmer":      (0.009, 0.12),
    "MDVP:Shimmer(dB)":  (0.08, 1.2),
    "Shimmer:APQ3":      (0.004, 0.06),
    "Shimmer:APQ5":      (0.006, 0.08),
    "MDVP:APQ":          (0.007, 0.09),
    "Shimmer:DDA":       (0.012, 0.18),
    "NHR":               (0.0005, 0.32),
    "HNR":               (8.0, 33.0),
    "RPDE":              (0.25, 0.75),
    "DFA":               (0.50, 0.85),
    "spread1":           (-9.0, -2.0),
    "spread2":           (0.08, 0.45),
    "D2":                (1.5, 3.0),
    "PPE":               (0.08, 0.50),
}


# Features críticas que deben estar en rango para considerar la extracción válida
# Son las que más se distorsionan con audio de celular.
# RPDE/DFA se quitaron de esta lista (2026-06-16): ya no alimentan al modelo
# de inferencia (ver PARKINSON_MODEL_FEATURE_ORDER en constants.py), así que
# no tiene sentido que sigan bloqueando la validez de una extracción.
CRITICAL_FEATURES = [
    "MDVP:Fo(Hz)",      # Frecuencia fundamental - debe ser razonable
    "HNR",              # Relación armónico-ruido - debe ser positiva
    "NHR",              # Ruido-armónicos - debe ser pequeño
]


def validate_features(features: Dict[str, float]) -> Dict[str, object]:
    """
    Valida que las features extraídas estén dentro de rangos plausibles
    comparados con el dataset UCI.

    Args:
        features: Diccionario de features extraídas del audio

    Returns:
        Dict con:
            - "valid": bool - True si las features son plausibles
            - "out_of_range_pct": float - porcentaje de features fuera de rango
            - "critical_failures": list - features críticas que fallaron
            - "message": str - mensaje descriptivo
    """
    total = 0
    out_of_range = 0
    critical_failures = []
    details = []

    for feature, (lo, hi) in UCI_RANGES.items():
        if feature not in features:
            out_of_range += 1
            total += 1
            if feature in CRITICAL_FEATURES:
                critical_failures.append(feature)
            details.append({
                "feature": feature,
                "value": None,
                "range": (lo, hi),
                "in_range": False,
                "reason": "missing"
            })
            continue

        val = features[feature]
        total += 1

        if val < lo or val > hi:
            out_of_range += 1
            if feature in CRITICAL_FEATURES:
                critical_failures.append(feature)
            details.append({
                "feature": feature,
                "value": val,
                "range": (lo, hi),
                "in_range": False,
                "reason": f"{val:.6f} fuera de [{lo:.6f}, {hi:.6f}]"
            })
        else:
            details.append({
                "feature": feature,
                "value": val,
                "range": (lo, hi),
                "in_range": True,
                "reason": "ok"
            })

    out_of_range_pct = (out_of_range / total * 100) if total > 0 else 100

    # Decidir validez
    # - Si >50% de features están fuera de rango → inválido
    # - Si alguna feature crítica falla → inválido
    # - Si HNR es negativo → inválido (imposible físicamente)
    is_valid = True
    message_parts = []

    if out_of_range_pct > 50:
        is_valid = False
        message_parts.append(
            f"{out_of_range_pct:.0f}% de features fuera de rango UCI"
        )

    if critical_failures:
        is_valid = False
        message_parts.append(
            f"Features críticas fuera de rango: {', '.join(critical_failures)}"
        )

    # Verificación específica: HNR nunca debe ser negativo
    hnr = features.get("HNR", 0)
    if hnr < 0:
        is_valid = False
        message_parts.append(f"HNR negativo ({hnr:.2f}) - imposible físicamente")

    # Verificación específica: NHR no debe ser > 1
    nhr = features.get("NHR", 0)
    if nhr > 1.0:
        is_valid = False
        message_parts.append(f"NHR anormalmente alto ({nhr:.4f})")

    message = "; ".join(message_parts) if message_parts else "Features dentro de rangos esperados"

    return {
        "valid": is_valid,
        "out_of_range_pct": out_of_range_pct,
        "out_of_range_count": out_of_range,
        "total_features": total,
        "critical_failures": critical_failures,
        "message": message,
        "details": details,
    }


def get_feature_quality_score(features: Dict[str, float]) -> float:
    """
    Calcula un puntaje de calidad de 0.0 a 1.0 basado en cuántas features
    están dentro de rangos esperados.

    1.0 = extracción perfecta (todas las features en rango)
    0.0 = extracción completamente fallida
    """
    result = validate_features(features)
    if result["total_features"] == 0:
        return 0.0
    in_range = result["total_features"] - result["out_of_range_count"]
    score = in_range / result["total_features"]

    # Penalizar si hay features críticas fallidas
    penalty = len(result["critical_failures"]) * 0.15
    score = max(0.0, score - penalty)

    return score


def sanitize_features(features: Dict[str, float]) -> Dict[str, float]:
    """
    Sanea (normaliza) las features extraídas de audio aplicando **clamping**
    a los rangos del dataset UCI Oxford.

    Esta es una solución **temporal** para la demostración: cuando la grabación
    de audio produce parámetros inconsistentes (fuera de rango), esta función
    los ajusta al límite más cercano del rango esperado por el modelo.

    El clamping se aplica feature por feature usando los rangos definidos en
    ``UCI_RANGES``. Las features que no están en ``UCI_RANGES`` se dejan
    intactas.

    Parameters
    ----------
    features : Dict[str, float]
        Diccionario de features extraídas del audio (posiblemente con valores
        aberrantes).

    Returns
    -------
    Dict[str, float]
        Nuevo diccionario con todas las features ajustadas a rangos válidos.

    Example
    -------
    >>> sanitize_features({"MDVP:Fo(Hz)": 500.0, "HNR": -5.0, "NHR": 2.5})
    {"MDVP:Fo(Hz)": 260.0, "HNR": 8.0, "NHR": 0.32}
    """
    sanitized = {}
    clamped_count = 0
    total_uci = 0

    for feature, value in features.items():
        if feature in UCI_RANGES:
            total_uci += 1
            lo, hi = UCI_RANGES[feature]
            if value < lo:
                sanitized[feature] = lo
                clamped_count += 1
                logger.debug(
                    "sanitize_features: %s = %.6f → clamp inferior a %.6f",
                    feature, value, lo,
                )
            elif value > hi:
                sanitized[feature] = hi
                clamped_count += 1
                logger.debug(
                    "sanitize_features: %s = %.6f → clamp superior a %.6f",
                    feature, value, hi,
                )
            else:
                sanitized[feature] = value
        else:
            # Feature no definida en UCI_RANGES, se pasa tal cual.
            sanitized[feature] = value

    if clamped_count > 0:
        logger.info(
            "sanitize_features: %d/%d features fueron ajustadas a rangos UCI "
            "(solución temporal para la demo)",
            clamped_count, total_uci,
        )

    return sanitized

