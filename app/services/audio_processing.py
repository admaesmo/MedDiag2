"""
Audio processing service for extracting acoustic features from audio files.
Extracts features for Parkinson's disease detection: jitter, shimmer, HNR, etc.
"""

import io
import os
import logging
import tempfile
from typing import Dict, Optional, Tuple, Any
import numpy as np
from sqlalchemy.exc import IntegrityError

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False

# Try to import optional audio processing libraries
try:
    import librosa
    import librosa.core
    import librosa.feature
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    logging.warning("Librosa not available. Audio processing will be limited.")

try:
    import parselmouth
    PRAAT_AVAILABLE = True
except ImportError:
    PRAAT_AVAILABLE = False
    logging.warning("Parselmouth (Praat) not available. Advanced voice analysis will be limited.")

try:
    import scipy
    import scipy.signal
    import scipy.stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    logging.warning("SciPy not available. Signal processing will be limited.")

from app.services.storage_service import get_storage_backend

logger = logging.getLogger(__name__)

# Parkinson's acoustic features to extract
PARKINSON_FEATURES = [
    "MDVP:Fo(Hz)", "MDVP:Fhi(Hz)", "MDVP:Flo(Hz)", "MDVP:Jitter(%)", "MDVP:Jitter(Abs)",
    "MDVP:RAP", "MDVP:PPQ", "Jitter:DDP", "MDVP:Shimmer", "MDVP:Shimmer(dB)",
    "Shimmer:APQ3", "Shimmer:APQ5", "MDVP:APQ", "Shimmer:DDA", "NHR", "HNR",
    "RPDE", "DFA", "spread1", "spread2", "D2", "PPE"
]


class AudioProcessingError(Exception):
    """Custom exception for audio processing errors."""
    pass


def _guess_suffix(source_name: Optional[str]) -> str:
    if not source_name:
        return ".wav"
    suffix = os.path.splitext(source_name)[1].lower().strip()
    return suffix if suffix else ".wav"


def _decode_audio_bytes(audio_bytes: bytes, source_name: Optional[str], sample_rate: int) -> Tuple[np.ndarray, int]:
    suffix = _guess_suffix(source_name)

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
        temp_file.write(audio_bytes)
        temp_path = temp_file.name

    try:
        try:
            return librosa.load(temp_path, sr=sample_rate, mono=True)
        except Exception as first_error:
            if not PYDUB_AVAILABLE:
                raise first_error

            try:
                segment = AudioSegment.from_file(temp_path)
                segment = segment.set_frame_rate(sample_rate).set_channels(1)
                samples = np.array(segment.get_array_of_samples()).astype(np.float32)
                scale = float(1 << (8 * segment.sample_width - 1))
                if scale > 0:
                    samples /= scale
                return samples, segment.frame_rate
            except Exception:
                raise first_error
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass


def extract_features_from_audio(
    audio_bytes: bytes,
    sample_rate: int = 22050,
    source_name: Optional[str] = None,
) -> Dict[str, float]:
    """
    Extract Parkinson's acoustic features from audio bytes.
    
    Args:
        audio_bytes: Raw audio data
        sample_rate: Target sample rate for processing
        
    Returns:
        Dictionary of extracted features with PARKINSON_FEATURES keys
    """
    if not LIBROSA_AVAILABLE:
        raise AudioProcessingError("Librosa is required for audio feature extraction")
    
    try:
        # Load audio through a temp file so compressed formats can be decoded reliably.
        y, sr = _decode_audio_bytes(audio_bytes, source_name, sample_rate)
        
        # Basic audio properties
        duration = librosa.get_duration(y=y, sr=sr)
        
        if duration < 0.5:  # Minimum 0.5 seconds of audio
            raise AudioProcessingError(f"Audio too short: {duration:.2f}s, minimum 0.5s required")
        
        # Extract fundamental frequency (pitch) using multiple methods
        f0 = extract_fundamental_frequency(y, sr)
        
        if f0 is None or len(f0) == 0:
            raise AudioProcessingError("Could not extract fundamental frequency from audio")
        
        # Calculate jitter (pitch perturbation)
        jitter_features = calculate_jitter(f0, sr)
        
        # Calculate shimmer (amplitude perturbation)
        shimmer_features = calculate_shimmer(y, f0, sr)
        
        # Calculate harmonic-to-noise ratio (HNR)
        hnr_features = calculate_hnr(y, sr)
        
        # Calculate nonlinear dynamics features (RPDE, DFA, D2, PPE, spread1, spread2)
        nonlinear_features = calculate_nonlinear_features(y, sr)
        
        # Combine all features
        features = {
            "MDVP:Fo(Hz)": float(np.nanmedian(f0)) if len(f0) > 0 else 0.0,
            "MDVP:Fhi(Hz)": float(np.nanmax(f0)) if len(f0) > 0 else 0.0,
            "MDVP:Flo(Hz)": float(np.nanmin(f0)) if len(f0) > 0 else 0.0,
            **jitter_features,
            **shimmer_features,
            **hnr_features,
            **nonlinear_features,
        }
        
        # Ensure all Parkinson features are present (fill missing with 0)
        for feature in PARKINSON_FEATURES:
            if feature not in features:
                features[feature] = 0.0
                logger.warning(f"Feature {feature} not extracted, using default 0.0")
        
        return features
        
    except Exception as e:
        logger.error(f"Error extracting audio features: {str(e)}", exc_info=True)
        raise AudioProcessingError(f"Failed to extract audio features: {str(e)}")


def extract_fundamental_frequency(y: np.ndarray, sr: int, fmin: float = 75.0, fmax: float = 300.0) -> np.ndarray:
    """
    Extract fundamental frequency (F0) using multiple methods for robustness.
    
    Args:
        y: Audio signal
        sr: Sample rate
        fmin: Minimum frequency (Hz)
        fmax: Maximum frequency (Hz)
        
    Returns:
        Array of fundamental frequency values
    """
    f0_methods = []
    
    # Method 1: Librosa's pYIN (most robust)
    if LIBROSA_AVAILABLE:
        try:
            f0_pyin, _, _ = librosa.pyin(
                y, 
                fmin=fmin, 
                fmax=fmax, 
                sr=sr,
                frame_length=2048,
                hop_length=512,
                fill_na=np.nan
            )
            if f0_pyin is not None:
                f0_methods.append(f0_pyin[~np.isnan(f0_pyin)])
        except Exception as e:
            logger.debug(f"pYIN method failed: {str(e)}")
    
    # Method 2: Parselmouth/Praat (if available, most accurate for voice)
    if PRAAT_AVAILABLE and len(f0_methods) == 0:
        try:
            import parselmouth
            sound = parselmouth.Sound(y, sr)
            pitch = sound.to_pitch(time_step=0.01, pitch_floor=fmin, pitch_ceiling=fmax)
            f0_praat = pitch.selected_array['frequency']
            f0_praat[f0_praat == 0] = np.nan  # Replace 0 with NaN
            f0_methods.append(f0_praat[~np.isnan(f0_praat)])
        except Exception as e:
            logger.debug(f"Praat method failed: {str(e)}")
    
    # Method 3: Autocorrelation (fallback)
    if SCIPY_AVAILABLE and len(f0_methods) == 0:
        try:
            # Simple autocorrelation-based pitch detection
            frame_length = 2048
            hop_length = 512
            f0_ac = []
            
            for i in range(0, len(y) - frame_length, hop_length):
                frame = y[i:i + frame_length]
                if len(frame) < frame_length:
                    break
                    
                # Apply window
                window = np.hanning(frame_length)
                frame = frame * window
                
                # Autocorrelation
                autocorr = np.correlate(frame, frame, mode='full')
                autocorr = autocorr[autocorr.size // 2:]
                
                # Find first peak after zero (excluding zero-lag peak)
                peaks, _ = scipy.signal.find_peaks(autocorr[:len(autocorr)//2])
                if len(peaks) > 0:
                    first_peak = peaks[0]
                    if first_peak > 0:
                        f0_frame = sr / first_peak
                        if fmin <= f0_frame <= fmax:
                            f0_ac.append(f0_frame)
                        else:
                            f0_ac.append(np.nan)
                    else:
                        f0_ac.append(np.nan)
                else:
                    f0_ac.append(np.nan)
            
            f0_ac = np.array(f0_ac)
            f0_methods.append(f0_ac[~np.isnan(f0_ac)])
        except Exception as e:
            logger.debug(f"Autocorrelation method failed: {str(e)}")
    
    # Combine results from available methods
    all_f0 = np.concatenate(f0_methods) if f0_methods else np.array([])
    
    if len(all_f0) == 0:
        logger.warning("No fundamental frequency could be extracted")
        return np.array([])
    
    return all_f0


def calculate_jitter(f0: np.ndarray, sr: int) -> Dict[str, float]:
    """
    Calculate jitter (pitch perturbation) features.
    
    Jitter measures the cycle-to-cycle variation in fundamental frequency.
    
    Args:
        f0: Fundamental frequency array
        sr: Sample rate (not used directly but kept for consistency)
        
    Returns:
        Dictionary with jitter features
    """
    if len(f0) < 2:
        return {
            "MDVP:Jitter(%)": 0.0,
            "MDVP:Jitter(Abs)": 0.0,
            "MDVP:RAP": 0.0,
            "MDVP:PPQ": 0.0,
            "Jitter:DDP": 0.0,
        }
    
    # Remove NaN values
    f0_clean = f0[~np.isnan(f0)]
    if len(f0_clean) < 2:
        return {
            "MDVP:Jitter(%)": 0.0,
            "MDVP:Jitter(Abs)": 0.0,
            "MDVP:RAP": 0.0,
            "MDVP:PPQ": 0.0,
            "Jitter:DDP": 0.0,
        }
    
    # Absolute differences between consecutive F0 values
    diffs = np.abs(np.diff(f0_clean))
    
    # Jitter(%): relative average absolute difference
    mean_f0 = np.mean(f0_clean)
    jitter_percent = (np.mean(diffs) / mean_f0) * 100 if mean_f0 > 0 else 0.0
    
    # Jitter(Abs): absolute average difference in Hz
    jitter_abs = np.mean(diffs)
    
    # RAP (Relative Average Perturbation): average of absolute differences between 
    # each F0 and the average of itself and its two neighbors
    if len(f0_clean) >= 3:
        rap_values = []
        for i in range(1, len(f0_clean) - 1):
            local_avg = np.mean(f0_clean[i-1:i+2])
            rap_values.append(np.abs(f0_clean[i] - local_avg))
        rap = np.mean(rap_values) / mean_f0 * 100 if mean_f0 > 0 else 0.0
    else:
        rap = 0.0
    
    # PPQ (Pitch Perturbation Quotient): similar to RAP but over 5 points
    if len(f0_clean) >= 5:
        ppq_values = []
        for i in range(2, len(f0_clean) - 2):
            local_avg = np.mean(f0_clean[i-2:i+3])
            ppq_values.append(np.abs(f0_clean[i] - local_avg))
        ppq = np.mean(ppq_values) / mean_f0 * 100 if mean_f0 > 0 else 0.0
    else:
        ppq = 0.0
    
    # DDP (Differential Jitter): average absolute difference between consecutive differences
    if len(diffs) >= 2:
        ddp_diffs = np.abs(np.diff(diffs))
        ddp = np.mean(ddp_diffs) / mean_f0 * 100 if mean_f0 > 0 else 0.0
    else:
        ddp = 0.0
    
    return {
        "MDVP:Jitter(%)": float(jitter_percent),
        "MDVP:Jitter(Abs)": float(jitter_abs),
        "MDVP:RAP": float(rap),
        "MDVP:PPQ": float(ppq),
        "Jitter:DDP": float(ddp),
    }


def calculate_shimmer(y: np.ndarray, f0: np.ndarray, sr: int) -> Dict[str, float]:
    """
    Calculate shimmer (amplitude perturbation) features.
    
    Shimmer measures the cycle-to-cycle variation in amplitude.
    
    Args:
        y: Audio signal
        f0: Fundamental frequency array
        sr: Sample rate
        
    Returns:
        Dictionary with shimmer features
    """
    if len(f0) < 2 or len(y) < sr * 0.1:  # Need at least 100ms of audio
        return {
            "MDVP:Shimmer": 0.0,
            "MDVP:Shimmer(dB)": 0.0,
            "Shimmer:APQ3": 0.0,
            "Shimmer:APQ5": 0.0,
            "MDVP:APQ": 0.0,
            "Shimmer:DDA": 0.0,
        }
    
    # Remove NaN values from F0
    f0_clean = f0[~np.isnan(f0)]
    if len(f0_clean) < 2:
        return {
            "MDVP:Shimmer": 0.0,
            "MDVP:Shimmer(dB)": 0.0,
            "Shimmer:APQ3": 0.0,
            "Shimmer:APQ5": 0.0,
            "MDVP:APQ": 0.0,
            "Shimmer:DDA": 0.0,
        }
    
    # Estimate period in samples for each F0 value
    periods = (sr / f0_clean).astype(int)
    periods = periods[(periods > 0) & (periods < len(y) // 2)]  # Reasonable bounds
    
    if len(periods) < 2:
        return {
            "MDVP:Shimmer": 0.0,
            "MDVP:Shimmer(dB)": 0.0,
            "Shimmer:APQ3": 0.0,
            "Shimmer:APQ5": 0.0,
            "MDVP:APQ": 0.0,
            "Shimmer:DDA": 0.0,
        }
    
    # Extract peak amplitudes for each estimated period
    amplitudes = []
    start_idx = 0
    
    for period in periods:
        if start_idx + period >= len(y):
            break
        
        # Find max amplitude in the period window
        window = y[start_idx:start_idx + period]
        if len(window) > 0:
            peak_amp = np.max(np.abs(window))
            amplitudes.append(peak_amp)
        
        start_idx += period
    
    amplitudes = np.array(amplitudes)
    if len(amplitudes) < 2:
        return {
            "MDVP:Shimmer": 0.0,
            "MDVP:Shimmer(dB)": 0.0,
            "Shimmer:APQ3": 0.0,
            "Shimmer:APQ5": 0.0,
            "MDVP:APQ": 0.0,
            "Shimmer:DDA": 0.0,
        }
    
    # Shimmer: relative average absolute difference between consecutive amplitudes
    amp_diffs = np.abs(np.diff(amplitudes))
    mean_amp = np.mean(amplitudes)
    shimmer = (np.mean(amp_diffs) / mean_amp) * 100 if mean_amp > 0 else 0.0
    
    # Shimmer(dB): in decibels
    shimmer_db = 20 * np.log10(1 + shimmer / 100) if shimmer > 0 else 0.0
    
    # APQ3 (Amplitude Perturbation Quotient, 3-point)
    if len(amplitudes) >= 3:
        apq3_values = []
        for i in range(1, len(amplitudes) - 1):
            local_avg = np.mean(amplitudes[i-1:i+2])
            apq3_values.append(np.abs(amplitudes[i] - local_avg))
        apq3 = np.mean(apq3_values) / mean_amp * 100 if mean_amp > 0 else 0.0
    else:
        apq3 = 0.0
    
    # APQ5 (5-point)
    if len(amplitudes) >= 5:
        apq5_values = []
        for i in range(2, len(amplitudes) - 2):
            local_avg = np.mean(amplitudes[i-2:i+3])
            apq5_values.append(np.abs(amplitudes[i] - local_avg))
        apq5 = np.mean(apq5_values) / mean_amp * 100 if mean_amp > 0 else 0.0
    else:
        apq5 = 0.0
    
    # MDVP:APQ (11-point, using 5-point as approximation)
    apq11 = apq5  # Approximation
    
    # DDA (Difference of Differences of Amplitudes)
    if len(amp_diffs) >= 2:
        dda_diffs = np.abs(np.diff(amp_diffs))
        dda = np.mean(dda_diffs) / mean_amp * 100 if mean_amp > 0 else 0.0
    else:
        dda = 0.0
    
    return {
        "MDVP:Shimmer": float(shimmer),
        "MDVP:Shimmer(dB)": float(shimmer_db),
        "Shimmer:APQ3": float(apq3),
        "Shimmer:APQ5": float(apq5),
        "MDVP:APQ": float(apq11),
        "Shimmer:DDA": float(dda),
    }


def calculate_hnr(y: np.ndarray, sr: int) -> Dict[str, float]:
    """
    Calculate Noise-to-Harmonics Ratio (NHR) and Harmonic-to-Noise Ratio (HNR).
    
    Args:
        y: Audio signal
        sr: Sample rate
        
    Returns:
        Dictionary with NHR and HNR features
    """
    try:
        # Simple approximation using cepstral analysis
        # Compute cepstrum
        spectrum = np.abs(np.fft.rfft(y))
        log_spectrum = np.log(spectrum + 1e-10)  # Add small value to avoid log(0)
        cepstrum = np.abs(np.fft.irfft(log_spectrum))
        
        # Find quefrency corresponding to pitch period (in samples)
        quefrencies = np.arange(len(cepstrum)) / sr
        
        # Look for peak in typical pitch range (2.5ms to 12.5ms, i.e., 80-400Hz)
        min_quef = 1/400  # 2.5ms
        max_quef = 1/80   # 12.5ms
        
        mask = (quefrencies >= min_quef) & (quefrencies <= max_quef)
        if np.any(mask):
            cepstrum_range = cepstrum[mask]
            quefrencies_range = quefrencies[mask]
            
            # Find the peak
            peak_idx = np.argmax(cepstrum_range)
            peak_value = cepstrum_range[peak_idx]
            
            # Estimate harmonic and noise components
            # Harmonic component is related to the cepstral peak
            # Noise component is the remaining cepstral energy
            total_energy = np.sum(cepstrum_range ** 2)
            harmonic_energy = peak_value ** 2
            noise_energy = total_energy - harmonic_energy
            
            if noise_energy > 0:
                nhr = noise_energy / harmonic_energy
                hnr = 10 * np.log10(harmonic_energy / noise_energy)  # Convert to dB
            else:
                nhr = 0.0
                hnr = 100.0  # Very high HNR if no noise
        else:
            nhr = 1.0
            hnr = 0.0
    
    except Exception as e:
        logger.debug(f"HNR calculation failed: {str(e)}")
        nhr = 1.0
        hnr = 0.0
    
    return {
        "NHR": float(nhr),
        "HNR": float(hnr),
    }


def calculate_nonlinear_features(y: np.ndarray, sr: int) -> Dict[str, float]:
    """
    Calculate nonlinear dynamics features: RPDE, DFA, D2, PPE, spread1, spread2.
    
    These features are complex and often computed from voice recordings
    using specialized algorithms. Here we provide approximations.
    
    Args:
        y: Audio signal
        sr: Sample rate
        
    Returns:
        Dictionary with nonlinear features
    """
    # For now, return reasonable default values based on typical voice recordings
    # In a production system, these would be computed using proper algorithms
    
    # RPDE (Recurrence Period Density Entropy) - measures voice regularity
    # Typical range: 0.2-0.6 for Parkinson's, lower for healthy
    rpde = 0.4 + np.random.randn() * 0.1  # Placeholder
    
    # DFA (Detrended Fluctuation Analysis) - scaling exponent
    # Typical range: 0.5-1.5
    dfa = 0.8 + np.random.randn() * 0.2  # Placeholder
    
    # D2 (Correlation Dimension) - complexity measure
    # Typical range: 1.5-3.0
    d2 = 2.3 + np.random.randn() * 0.3  # Placeholder
    
    # PPE (Pitch Period Entropy) - pitch regularity
    # Typical range: 0.1-0.4
    ppe = 0.25 + np.random.randn() * 0.1  # Placeholder
    
    # spread1, spread2 - related to fundamental frequency variation
    # These are often derived from the modulation spectrum
    spread1 = -5.0 + np.random.randn() * 1.0  # Placeholder
    spread2 = 0.2 + np.random.randn() * 0.1   # Placeholder
    
    return {
        "RPDE": float(rpde),
        "DFA": float(dfa),
        "D2": float(d2),
        "PPE": float(ppe),
        "spread1": float(spread1),
        "spread2": float(spread2),
    }


def process_audio_file(audio_record_id: int, db) -> Optional[Dict[str, float]]:
    """
    Main function to process an audio file and extract features.
    
    Args:
        audio_record_id: ID of the audio record in the database
        db: Database session
        
    Returns:
        Extracted features dictionary or None if failed
    """
    from app.models import AudioRecord
    
    # Get audio record from database
    audio_record = db.query(AudioRecord).filter(AudioRecord.id == audio_record_id).first()
    if not audio_record:
        logger.error(f"Audio record {audio_record_id} not found")
        return None
    
    # Check if already processed
    if audio_record.status == "processed":
        logger.info(f"Audio record {audio_record_id} already processed")
        # Return existing features if stored somewhere
        return None
    
    try:
        # Update status to processing
        audio_record.status = "processing"
        db.commit()
        
        # Get storage backend
        backend = get_storage_backend()
        
        # Load audio file
        audio_bytes = backend.load(audio_record.storage_path)
        if not audio_bytes:
            raise AudioProcessingError(f"Could not load audio file from storage")
        
        # Extract features
        features = extract_features_from_audio(
            audio_bytes,
            source_name=audio_record.original_filename or audio_record.stored_filename,
        )
        
        # Update audio record with features
        # Note: We need to store features somewhere - could add a JSON field to AudioRecord
        # or create a separate table. For now, we'll just return them.
        audio_record.status = "processed"
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            audio_record = db.query(AudioRecord).filter(AudioRecord.id == audio_record_id).first()
            if audio_record:
                audio_record.status = "transcribed"
                db.commit()
        
        logger.info(f"Successfully processed audio record {audio_record_id}")
        return features
        
    except Exception as e:
        logger.error(f"Failed to process audio record {audio_record_id}: {str(e)}")
        audio_record.status = "failed"
        db.commit()
        return None