"""Utilidades compartidas de decodificación de audio."""

from __future__ import annotations

import logging
import os
import tempfile
from typing import Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False


def guess_audio_suffix(source_name: Optional[str]) -> str:
    if not source_name:
        return ".wav"
    suffix = os.path.splitext(source_name)[1].lower().strip()
    return suffix if suffix else ".wav"


def decode_audio_bytes(
    audio_bytes: bytes,
    source_name: Optional[str] = None,
    sample_rate: Optional[int] = 22050,
) -> Tuple[np.ndarray, int]:
    """
    Decodifica bytes de audio a (señal, tasa_muestreo).

    Intenta librosa primero; si falla, usa pydub como respaldo.
    Ambas rutas producen señal mono. Con sample_rate=None se conserva
    la tasa nativa del archivo (útil para control de calidad).
    """
    if not LIBROSA_AVAILABLE:
        raise RuntimeError("librosa es requerido para decodificar audio")

    suffix = guess_audio_suffix(source_name)
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        try:
            return librosa.load(tmp_path, sr=sample_rate, mono=True)
        except Exception as first_err:
            if not PYDUB_AVAILABLE:
                raise first_err
            try:
                seg = AudioSegment.from_file(tmp_path)
                if sample_rate is not None:
                    seg = seg.set_frame_rate(sample_rate)
                seg = seg.set_channels(1)
                samples = np.array(seg.get_array_of_samples()).astype(np.float32)
                scale = float(1 << (8 * seg.sample_width - 1))
                if scale > 0:
                    samples /= scale
                return samples, seg.frame_rate
            except Exception:
                raise first_err
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
