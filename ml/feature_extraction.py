"""
feature_extraction.py
---------------------
Wavelet-based feature extraction for ECG heartbeat segments.

Compares three Daubechies mother wavelets:
    db1  (Haar)
    db2
    db4

For each wavelet, computes the detail / approximation coefficients
at each decomposition level and extracts statistical features:
    mean, std, energy, max, min  → per sub-band
"""

import numpy as np
import pywt


# ── Per-segment feature vector ────────────────────────────────

def _coeff_features(coeff: np.ndarray) -> np.ndarray:
    """Return 5 statistical features for one coefficient array."""
    return np.array([
        np.mean(coeff),
        np.std(coeff),
        np.sum(coeff ** 2),          # energy
        np.max(np.abs(coeff)),
        np.min(np.abs(coeff)),
    ])


def wavelet_features(segment: np.ndarray,
                     wavelet: str = "db4",
                     level: int = 4) -> np.ndarray:
    """
    Decompose one heartbeat segment with a DWT and return a feature vector.

    Parameters
    ----------
    segment : 1-D array  (one heartbeat window)
    wavelet : mother wavelet name  ('db1', 'db2', 'db4')
    level   : decomposition depth

    Returns
    -------
    features : 1-D ndarray
    """
    coeffs = pywt.wavedec(segment, wavelet, level=level)
    # coeffs = [cA_n, cD_n, cD_{n-1}, ..., cD_1]
    features = np.concatenate([_coeff_features(c) for c in coeffs])
    return features


# ── Build feature matrix for all segments ────────────────────

def extract_features(segments: np.ndarray,
                     wavelet: str = "db4",
                     level: int = 4) -> np.ndarray:
    """
    Extract wavelet features from all segments.

    Parameters
    ----------
    segments : ndarray of shape (N_beats, window_length)
    wavelet  : 'db1', 'db2', or 'db4'
    level    : DWT decomposition level

    Returns
    -------
    X : ndarray of shape (N_beats, n_features)
    """
    if len(segments) == 0:
        return np.empty((0,))
    return np.vstack([wavelet_features(s, wavelet, level) for s in segments])


# ── Compare all three wavelets ────────────────────────────────

WAVELETS = ["db1", "db2", "db4"]


def extract_all_wavelets(segments: np.ndarray,
                         level: int = 4) -> dict:
    """
    Return a dict  { wavelet_name : feature_matrix }  for db1/db2/db4.
    """
    return {w: extract_features(segments, w, level) for w in WAVELETS}
