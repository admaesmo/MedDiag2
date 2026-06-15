"""
Endpoint ligero para extracción directa de biomarcadores de voz desde audio cargado.
"""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.schemas.voice_biomarkers import (
    ParkinsonModelBridgeResponse,
    ParkinsonInferenceResponse,
    ParkinsonModelInputResponse,
    VoiceBiomarkerAudioMetadata,
    VoiceBiomarkerExtractionResponse,
    VoiceBiomarkerSet,
)
from app.services import audio_service
from app.services.voice_biomarkers import (
    TARGET_WAV_FORMAT,
    VoiceBiomarkerError,
    build_parkinson_model_bridge,
    build_parkinson_model_input,
    cleanup_prepared_audio,
    extract_parkinson_model_features,
    extract_voice_biomarkers,
    prepare_audio_for_voice_biomarkers,
    run_parkinson_direct_inference,
)

router = APIRouter(prefix="/audio/biomarkers", tags=["audio", "voice-biomarkers"])


@router.post("/extract", response_model=VoiceBiomarkerExtractionResponse)
async def extract_voice_biomarkers_endpoint(file: UploadFile = File(...)):
    """
    Recibe un archivo de audio, lo normaliza a mono/16 kHz/WAV y devuelve los
    biomarcadores Parselmouth solicitados junto con una carga lista para
    inferencia directa según el contrato actual de 22 características.
    """

    audio_bytes = await file.read()
    file_size = len(audio_bytes)

    try:
        audio_service.validate_audio_file(file.content_type, file_size)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    prepared_audio = None
    try:
        prepared_audio = prepare_audio_for_voice_biomarkers(
            audio_bytes=audio_bytes,
            source_name=file.filename,
        )

        # --- COMPUERTA QA/QC antes del pre-análisis ---
        # Un audio que no cumple los requisitos no debe generar pre-análisis ni inferencia.
        import soundfile as sf
        from app.services.quality_control import analizar_signal

        waveform, wav_sr = sf.read(prepared_audio.temp_wav_path)
        qc = analizar_signal(waveform, wav_sr)
        if not qc.is_valid:
            reason = qc.rejection_reason or "El audio no superó el control de calidad."
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Control de calidad rechazado: {reason}",
            )

        biomarkers = extract_voice_biomarkers(prepared_audio)
        bridge = build_parkinson_model_bridge(biomarkers)
        model_features = extract_parkinson_model_features(prepared_audio)
        model_input = build_parkinson_model_input(model_features)
        inference = run_parkinson_direct_inference(model_features)

        return VoiceBiomarkerExtractionResponse(
            audio=VoiceBiomarkerAudioMetadata(
                original_filename=file.filename,
                content_type=file.content_type,
                sample_rate_hz=prepared_audio.sample_rate_hz,
                channels=prepared_audio.channels,
                normalized_format=TARGET_WAV_FORMAT,
                duration_seconds=prepared_audio.duration_seconds,
            ),
            biomarkers=VoiceBiomarkerSet(**biomarkers),
            parkinson_model_bridge=ParkinsonModelBridgeResponse(**bridge),
            parkinson_model_input=ParkinsonModelInputResponse(**model_input),
            parkinson_inference=ParkinsonInferenceResponse(**inference),
        )
    except HTTPException:
        raise
    except VoiceBiomarkerError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error inesperado al extraer biomarcadores de voz: {exc}",
        )
    finally:
        cleanup_prepared_audio(prepared_audio)
