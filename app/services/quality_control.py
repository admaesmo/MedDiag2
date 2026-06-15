"""
Servicio de Control de Calidad — compuerta de validación de señal de audio.

Analiza el audio crudo para detectar:
  - Duración válida
  - Recorte (saturación de pico)
  - Energía RMS
  - Relación señal/ruido (SNR)
  - Proporción de silencio
  - Piso de ruido
  - Ancho de banda ocupado

Genera un AudioQualityReport que debe ser aprobado antes de la extracción
de biomarcadores.
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple

import numpy as np

from sqlalchemy.orm import Session

from app.models import AudioRecord, AudioQualityReport
from app.schemas.quality_control import QualityControlResult
from app.services.audio_utils import decode_audio_bytes

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Umbrales configurables  (podrían promoverse a settings / vars de entorno)
# ---------------------------------------------------------------------------

DURACION_MINIMA_S = 0.8          # segundos
MAX_RAZON_RECORTE = 0.01         # 1 % de muestras recortadas → rechazar
RMS_MINIMO = 0.005               # por debajo → demasiado silencio / baja energía
MAX_RAZON_SILENCIO = 0.90        # 90 % de tramas casi en cero → rechazar. Las grabaciones de micrófono incluyen
                                 # silencio inicial/final y pausas naturales; un umbral más estricto (0.60) rechazaba
                                 # casi toda voz real. Mejora futura: recortar silencio (VAD) antes de medir.
SNR_MINIMO_DB = 10.0             # menos de 10 dB → demasiado ruidoso
UMBRAL_RECORTE = 0.98            # |muestra| >= umbral → candidato a recorte


def _cargar_audio_desde_registro(audio_record: AudioRecord) -> Tuple[np.ndarray, int]:
    """Carga y decodifica un archivo de audio desde almacenamiento."""
    from app.services.storage_service import get_storage_backend

    backend = get_storage_backend()
    audio_bytes = backend.load(audio_record.storage_path)
    if not audio_bytes:
        raise RuntimeError(f"No se pudo cargar el audio desde {audio_record.storage_path}")

    source_name = getattr(audio_record, "original_filename", None) or getattr(audio_record, "stored_filename", None)
    return decode_audio_bytes(audio_bytes, source_name=source_name, sample_rate=None)


def _calcular_snr(y: np.ndarray, sr: int, marco_ms: int = 30) -> Optional[float]:
    """Estima la SNR mediante heurística de actividad vocal (división por percentiles de energía)."""
    len_marco = int(sr * marco_ms / 1000)
    if len(y) < len_marco * 2:
        return None

    tramas = y[: (len(y) // len_marco) * len_marco].reshape(-1, len_marco)
    rms_por_trama = np.sqrt(np.mean(tramas ** 2, axis=1))

    if rms_por_trama.size < 4:
        return None

    # 25 % inferior de tramas → estimación de piso de ruido
    tramas_ruido = rms_por_trama[np.argsort(rms_por_trama)[: max(1, rms_por_trama.size // 4)]]
    rms_ruido = float(np.mean(tramas_ruido)) + 1e-12

    # 25 % superior de tramas → señal
    tramas_senal = rms_por_trama[np.argsort(-rms_por_trama)[: max(1, rms_por_trama.size // 4)]]
    rms_senal = float(np.mean(tramas_senal))

    relacion = rms_senal / rms_ruido
    if relacion <= 0:
        return None
    return 20.0 * np.log10(relacion)


def _calcular_ancho_banda(y: np.ndarray, sr: int, fraccion_energia: float = 0.95) -> float:
    """Estima la banda de frecuencia que contiene *fraccion_energia* de la energía total."""
    espectro = np.abs(np.fft.rfft(y))
    potencia = espectro ** 2
    total = np.sum(potencia)
    if total <= 0:
        return 0.0

    cumsum = np.cumsum(potencia)
    indice_corte = int(np.searchsorted(cumsum, total * fraccion_energia))
    frecuencias = np.fft.rfftfreq(len(y), d=1.0 / sr)
    if indice_corte < len(frecuencias):
        return float(frecuencias[indice_corte])
    return float(frecuencias[-1]) if len(frecuencias) > 0 else 0.0


def analizar_audio(audio_record: AudioRecord) -> QualityControlResult:
    """
    Ejecuta controles de calidad sobre *audio_record* y devuelve un resultado estructurado.

    Pasos realizados:
      1. Carga y decodificación del audio
      2. Medición de duración, RMS, pico, recorte
      3. Estimación de SNR
      4. Medición de proporción de silencio, piso de ruido, ancho de banda
      5. Combinación en un veredicto de aprobación/rechazo con puntuación
    """
    y, sr = _cargar_audio_desde_registro(audio_record)
    return analizar_signal(y, sr)


def analizar_signal(y: np.ndarray, sr: int) -> QualityControlResult:
    """
    Ejecuta los controles de calidad directamente sobre una señal decodificada.

    Permite reutilizar la compuerta de QA/QC sin un AudioRecord persistido
    (por ejemplo, durante la extracción de biomarcadores previa al pre-análisis).
    """
    duracion_s = float(len(y)) / sr

    # --- Métricas básicas ---
    rms = float(np.sqrt(np.mean(y ** 2)))
    pico = float(np.max(np.abs(y)))
    mascara_recorte = np.abs(y) >= UMBRAL_RECORTE
    conteo_recorte = int(np.sum(mascara_recorte))
    razon_recorte = conteo_recorte / max(len(y), 1)

    # --- Proporción de silencio (tramas con RMS < 1 % del pico) ---
    len_marco = int(sr * 0.020)  # tramas de 20 ms
    if len_marco < 1:
        len_marco = max(1, len(y) // 100)
    tramas = y[: (len(y) // len_marco) * len_marco].reshape(-1, len_marco)
    rms_trama = np.sqrt(np.mean(tramas ** 2, axis=1))
    umbral_silencio = 0.01 * (pico + 1e-12)
    razon_silencio = float(np.mean(rms_trama < umbral_silencio))

    # --- SNR ---
    snr_db = _calcular_snr(y, sr)

    # --- Piso de ruido (dB) ---
    piso_ruido_db = float(20.0 * np.log10(np.percentile(np.abs(y), 5) + 1e-12))

    # --- Ancho de banda ---
    bw = _calcular_ancho_banda(y, sr)

    # --- Lógica de puntuación ---
    puntuacion = 1.0
    razones: list[str] = []

    # Duración
    if duracion_s < DURACION_MINIMA_S:
        razones.append(f"Duración {duracion_s:.2f}s < mín {DURACION_MINIMA_S}s")
    else:
        puntuacion *= min(1.0, duracion_s / 3.0)  # penaliza grabaciones muy cortas

    # Recorte
    if razon_recorte > MAX_RAZON_RECORTE:
        razones.append(f"Recorte {razon_recorte:.4f} > máx {MAX_RAZON_RECORTE}")
        puntuacion *= 0.0  # rechazo duro
    elif razon_recorte > 0:
        puntuacion *= (1.0 - razon_recorte * 5.0)

    # RMS (demasiado bajo)
    if rms < RMS_MINIMO:
        razones.append(f"Energía RMS {rms:.5f} < mín {RMS_MINIMO}")
        puntuacion *= max(0.0, rms / RMS_MINIMO)

    # Proporción de silencio (penalización suave; sólo rechazo si es casi todo silencio)
    if razon_silencio > MAX_RAZON_SILENCIO:
        razones.append(f"Silencio {razon_silencio:.3f} > máx {MAX_RAZON_SILENCIO}")
        puntuacion *= 0.0  # rechazo duro: grabación prácticamente vacía
    else:
        puntuacion *= (1.0 - razon_silencio * 0.5)

    # SNR
    if snr_db is not None and snr_db < SNR_MINIMO_DB:
        razones.append(f"SNR {snr_db:.1f} dB < mín {SNR_MINIMO_DB} dB")
        puntuacion *= max(0.0, snr_db / SNR_MINIMO_DB)

    # Acotar puntuación a [0, 1]
    puntuacion = max(0.0, min(1.0, puntuacion))

    es_valido = len(razones) == 0 or puntuacion >= 0.3
    motivo_rechazo = "; ".join(razones) if razones else None

    return QualityControlResult(
        is_valid=es_valido,
        quality_score=round(puntuacion, 4),
        rejection_reason=motivo_rechazo,
        duration_seconds=duracion_s,
        rms_energy=float(rms),
        peak_amplitude=float(pico),
        clipping_detected=razon_recorte > 0,
        clipping_ratio=razon_recorte,
        snr_db=round(snr_db, 2) if snr_db is not None else None,
        silence_ratio=razon_silencio,
        noise_floor_db=round(piso_ruido_db, 2),
        bandwidth_hz=round(bw, 1),
    )


def ejecutar_control_calidad(db: Session, audio_record_id: int) -> AudioQualityReport:
    """
    Ciclo completo de control de calidad: analizar → persistir → actualizar estado.

    Devuelve el registro AudioQualityReport persistido.
    """
    record = db.query(AudioRecord).filter(AudioRecord.id == audio_record_id).first()
    if not record:
        raise ValueError(f"AudioRecord {audio_record_id} no encontrado")

    resultado = analizar_audio(record)

    reporte = AudioQualityReport(
        audio_record_id=audio_record_id,
        is_valid=resultado.is_valid,
        quality_score=resultado.quality_score,
        rejection_reason=resultado.rejection_reason,
        duration_seconds=resultado.duration_seconds,
        rms_energy=resultado.rms_energy,
        peak_amplitude=resultado.peak_amplitude,
        clipping_detected=resultado.clipping_detected,
        clipping_ratio=resultado.clipping_ratio,
        snr_db=resultado.snr_db,
        silence_ratio=resultado.silence_ratio,
        noise_floor_db=resultado.noise_floor_db,
        bandwidth_hz=resultado.bandwidth_hz,
    )
    db.add(reporte)

    # Actualizar estado del registro de audio
    if resultado.is_valid:
        record.status = "quality_checked"
    else:
        record.status = "rejected"
    db.commit()
    db.refresh(reporte)
    return reporte


def obtener_ultimo_reporte_calidad(db: Session, audio_record_id: int) -> Optional[AudioQualityReport]:
    """Devuelve el reporte de calidad más reciente para un registro de audio."""
    return (
        db.query(AudioQualityReport)
        .filter(AudioQualityReport.audio_record_id == audio_record_id)
        .order_by(AudioQualityReport.created_at.desc())
        .first()
    )


# Alias conservados para imports existentes en API/pipeline.
analyse_audio = analizar_audio
run_quality_check = ejecutar_control_calidad
get_latest_quality_report = obtener_ultimo_reporte_calidad
