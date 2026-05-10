"""
ecg_preprocessing.py
--------------------
Preprocessing pipeline for ECG signals:
  1. Bandpass filter  (0.5 – 40 Hz)
  2. Baseline wander removal  (high-pass 0.5 Hz)
  3. Notch filter  (50 / 60 Hz powerline)
  4. Pan-Tompkins R-peak detection
  5. Heartbeat segmentation  (window around each R-peak)
"""

import numpy as np
from scipy.signal import butter, filtfilt, iirnotch, find_peaks


# ── Filters ──────────────────────────────────────────────────

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


# ── R-peak detection (simplified Pan-Tompkins) ───────────────

def detect_r_peaks(signal: np.ndarray, fs: float) -> np.ndarray:
    """Detect R-peaks using derivative + squaring + moving window."""
    # 1. Differentiate
    diff = np.diff(signal, prepend=signal[0])
    # 2. Square
    squared = diff ** 2
    # 3. Moving average (150 ms window)
    win = int(0.150 * fs)
    if win < 1:
        win = 1
    kernel = np.ones(win) / win
    mwa = np.convolve(squared, kernel, mode="same")
    # 4. Find peaks with minimum distance ~0.6 s (40 bpm lower bound)
    min_dist = int(0.6 * fs)
    peaks, _ = find_peaks(mwa, distance=min_dist,
                          height=np.mean(mwa) * 0.5)
    return peaks


# ── Heartbeat segmentation ────────────────────────────────────

def segment_heartbeats(signal: np.ndarray, r_peaks: np.ndarray,
                       fs: float,
                       pre_ms: float = 200,
                       post_ms: float = 400) -> np.ndarray:
    """
    Extract fixed-length windows around each R-peak.

    Returns
    -------
    segments : ndarray of shape (N_beats, window_length)
    """
    pre  = int(pre_ms  / 1000 * fs)
    post = int(post_ms / 1000 * fs)
    length = pre + post
    segments = []
    for r in r_peaks:
        start = r - pre
        end   = r + post
        if start < 0 or end > len(signal):
            continue
        segments.append(signal[start:end])
    if len(segments) == 0:
        return np.empty((0, length))
    return np.array(segments)


# ── Full pipeline ─────────────────────────────────────────────

def preprocess_ecg(signal: np.ndarray, fs: float = 1000.0):
    """
    Run the full preprocessing pipeline.

    Returns
    -------
    clean    : filtered ECG signal
    r_peaks  : indices of detected R-peaks
    segments : heartbeat segments, shape (N, window_length)
    """
    clean = baseline_removal(signal, fs)
    clean = bandpass_filter(clean, fs)
    clean = notch_filter(clean, fs)
    r_peaks  = detect_r_peaks(clean, fs)
    segments = segment_heartbeats(clean, r_peaks, fs)
    return clean, r_peaks, segments
