"""
ecg_preprocessing.py
--------------------
Preprocessing pipeline for ECG signals:
  1. Baseline wander removal
  2. Bandpass filter (0.5-40 Hz)
  3. Notch filter (50 Hz powerline)
  4. NeuroKit R-peak detection with local dominant-peak refinement
  5. Heartbeat segmentation around each R-peak
"""

from __future__ import annotations

import numpy as np
from scipy.signal import butter, filtfilt, find_peaks, iirnotch

try:
    import neurokit2 as nk
except ImportError:
    nk = None


def bandpass_filter(signal: np.ndarray, fs: float,
                    low: float = 0.5, high: float = 40.0,
                    order: int = 4) -> np.ndarray:
    """Butterworth bandpass filter."""
    nyq = fs / 2.0
    b, a = butter(order, [low / nyq, high / nyq], btype="band")
    return filtfilt(b, a, signal)


def baseline_removal(signal: np.ndarray, fs: float,
                     cutoff: float = 0.5, order: int = 2) -> np.ndarray:
    """High-pass filter to remove baseline wander."""
    nyq = fs / 2.0
    b, a = butter(order, cutoff / nyq, btype="high")
    return filtfilt(b, a, signal)


def notch_filter(signal: np.ndarray, fs: float,
                 freq: float = 50.0, Q: float = 30.0) -> np.ndarray:
    """Notch filter for powerline interference."""
    nyq = fs / 2.0
    b, a = iirnotch(freq / nyq, Q)
    return filtfilt(b, a, signal)


def _dominant_qrs_polarity(signal: np.ndarray) -> int:
    """Return 1 for upright QRS complexes, -1 for inverted complexes."""
    high = np.percentile(signal, 99)
    low = abs(np.percentile(signal, 1))
    return 1 if high >= low else -1


def _refine_to_local_r_peak(signal: np.ndarray,
                            peaks: np.ndarray,
                            fs: float,
                            search_ms: float = 90) -> np.ndarray:
    """
    Move detector estimates onto the dominant ECG peak in a local QRS window.

    Energy-based detectors can mark a point after the actual R wave. This makes
    the ECG Viewer marker sit on the tall R deflection itself.
    """
    if len(peaks) == 0:
        return np.asarray(peaks, dtype=int)

    radius = max(1, int(search_ms / 1000 * fs))
    polarity = _dominant_qrs_polarity(signal)
    refined = []

    for peak in np.asarray(peaks, dtype=int):
        start = max(0, peak - radius)
        end = min(len(signal), peak + radius + 1)
        if end <= start:
            continue
        window = signal[start:end]
        local = np.argmax(window) if polarity > 0 else np.argmin(window)
        refined.append(start + int(local))

    refined = np.array(sorted(set(refined)), dtype=int)
    min_dist = max(1, int(0.250 * fs))
    deduped = []
    for peak in refined:
        if not deduped or peak - deduped[-1] >= min_dist:
            deduped.append(int(peak))
        else:
            prev = deduped[-1]
            better = peak if polarity * signal[peak] > polarity * signal[prev] else prev
            deduped[-1] = int(better)
    return np.array(deduped, dtype=int)


def _detect_r_peaks_neurokit(signal: np.ndarray, fs: float) -> np.ndarray:
    """Use NeuroKit when installed."""
    if nk is None:
        return np.empty(0, dtype=int)
    try:
        _, info = nk.ecg_peaks(signal, sampling_rate=int(round(fs)), method="neurokit")
        peaks = np.asarray(info.get("ECG_R_Peaks", []), dtype=int)
        return _refine_to_local_r_peak(signal, peaks, fs)
    except Exception:
        return np.empty(0, dtype=int)


def _detect_r_peaks_fallback(signal: np.ndarray, fs: float) -> np.ndarray:
    """Fallback detector used when NeuroKit is unavailable."""
    polarity = _dominant_qrs_polarity(signal)
    target = polarity * signal
    min_dist = max(1, int(0.350 * fs))
    prominence = max(np.std(target) * 0.7, 1e-9)
    height = np.percentile(target, 80)
    peaks, _ = find_peaks(
        target,
        distance=min_dist,
        prominence=prominence,
        height=height,
    )

    if len(peaks) == 0:
        diff = np.diff(signal, prepend=signal[0])
        squared = diff ** 2
        win = max(1, int(0.150 * fs))
        kernel = np.ones(win) / win
        mwa = np.convolve(squared, kernel, mode="same")
        peaks, _ = find_peaks(
            mwa,
            distance=max(1, int(0.6 * fs)),
            height=np.mean(mwa) * 0.5,
        )

    return _refine_to_local_r_peak(signal, peaks, fs)


def detect_r_peaks(signal: np.ndarray, fs: float) -> np.ndarray:
    """Detect R-peaks with NeuroKit when available, plus local peak refinement."""
    signal = np.asarray(signal, dtype=float)
    signal = np.nan_to_num(signal, nan=0.0, posinf=0.0, neginf=0.0)

    peaks = _detect_r_peaks_neurokit(signal, fs)
    if len(peaks) > 0:
        return peaks
    return _detect_r_peaks_fallback(signal, fs)


def segment_heartbeats(signal: np.ndarray, r_peaks: np.ndarray,
                       fs: float,
                       pre_ms: float = 200,
                       post_ms: float = 400) -> np.ndarray:
    """
    Extract fixed-length windows around each R-peak.

    Returns an ndarray of shape (N_beats, window_length).
    """
    pre = int(pre_ms / 1000 * fs)
    post = int(post_ms / 1000 * fs)
    length = pre + post
    segments = []
    for r in r_peaks:
        start = r - pre
        end = r + post
        if start < 0 or end > len(signal):
            continue
        segments.append(signal[start:end])
    if len(segments) == 0:
        return np.empty((0, length))
    return np.array(segments)


def preprocess_ecg(signal: np.ndarray, fs: float = 1000.0):
    """
    Run the full preprocessing pipeline.

    Returns clean signal, R-peak indices, and heartbeat segments.
    """
    clean = baseline_removal(signal, fs)
    clean = bandpass_filter(clean, fs)
    clean = notch_filter(clean, fs)
    r_peaks = detect_r_peaks(clean, fs)
    segments = segment_heartbeats(clean, r_peaks, fs)
    return clean, r_peaks, segments
