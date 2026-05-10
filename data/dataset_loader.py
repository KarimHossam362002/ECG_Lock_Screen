"""
dataset_loader.py
-----------------
Load and prepare ECG data from the PTB database.

PTB Database: https://physionet.org/content/ptbdb/1.0.0/
  • 549 records from 290 subjects
  • Sampling frequency: 1000 Hz
  • 15 leads available

Install wfdb:
    pip install wfdb

Usage:
    from data.dataset_loader import load_ptb_dataset
    X_train, X_test, y_train, y_test, subject_names, raw_signals =
        load_ptb_dataset(data_dir)
"""

from __future__ import annotations

import os
import re
from typing import List, Tuple

import numpy as np
from sklearn.model_selection import train_test_split


try:
    import wfdb  # pylint: disable=unused-import
except ImportError:
    wfdb = None


from ml.ecg_preprocessing import preprocess_ecg
from ml.feature_extraction import extract_features


N_SUBJECTS       = 5      # number of subjects (UI caps this for the HCI demo)
LEAD_INDEX       = 1      # lead II — column index in WFDB signal (matches PTB *.hea order)
FS               = 1000.0 # PTB sampling frequency (Hz)
TEST_SIZE        = 0.3    # 70 % train / 30 % test split
RANDOM_STATE     = 42

# Using every record for every included patient is very slow; sorted by filename then truncated.
MAX_RECORDS_PER_PATIENT = 12


def _is_placeholder_data_path(data_dir: str | None) -> bool:
    s = (data_dir or "").strip()
    return (not s) or ("demo" in s.lower() and "path" in s.lower())


def _looks_like_ptbdb_root(root: str) -> bool:
    if not root or not os.path.isdir(root):
        return False
    for entry in os.listdir(root):
        sub = os.path.join(root, entry)
        if not os.path.isdir(sub):
            continue
        if entry.lower().startswith("patient"):
            for fn in os.listdir(sub):
                if fn.endswith(".hea"):
                    return True
    return False


def _patient_folder_sort_key(dirname: str) -> int | float:
    m = re.fullmatch(r"patient(\d+)", dirname, flags=re.I)
    return int(m.group(1)) if m else float("inf")


def _collect_ptbdb_records(root: str, max_subjects: int) -> Tuple[List[str], List[Tuple[str, int]]]:
    dirs = sorted(
        [d for d in os.listdir(root)
         if os.path.isdir(os.path.join(root, d))],
        key=_patient_folder_sort_key,
    )
    subject_dirs = [d for d in dirs if d.lower().startswith("patient")]
    if not subject_dirs:
        raise ValueError(f"No PTB patient folders found under {root}")

    picked = subject_dirs[: max(1, min(max_subjects, len(subject_dirs)))]
    subject_names = picked

    records: List[Tuple[str, int]] = []
    for sid, sdir in enumerate(picked):
        subject_path = os.path.join(root, sdir)
        hea_files = sorted(
            f for f in os.listdir(subject_path) if f.lower().endswith(".hea")
        )
        if MAX_RECORDS_PER_PATIENT is not None:
            hea_files = hea_files[: max(1, int(MAX_RECORDS_PER_PATIENT))]
        for fname in hea_files:
            rec_path = os.path.join(subject_path, fname[:-4])
            records.append((rec_path, sid))

    return subject_names, records


def _load_wfdb_single(record_path: str, lead: int = LEAD_INDEX) -> tuple[np.ndarray, float]:
    if wfdb is None:
        raise ImportError(
            "The PTB dataset requires the 'wfdb' package.\n"
            "Install dependencies: pip install wfdb"
        )
    record = wfdb.rdrecord(record_path)
    if record.p_signal is None or record.p_signal.size == 0:
        raise ValueError(f"No signal data loaded from {record_path}")
    ncol = record.p_signal.shape[1]
    if lead >= ncol or lead < 0:
        raise ValueError(f"Lead index {lead} out of range for {record_path} ({ncol} leads)")
    signal = np.asarray(record.p_signal[:, lead], dtype=float)
    signal = np.nan_to_num(signal, nan=0.0, posinf=0.0, neginf=0.0)
    return signal, float(record.fs)


def _load_demo_single(record_path: str) -> tuple[np.ndarray, float]:
    rng = np.random.default_rng(abs(hash(record_path)) % (2**31))
    length = int(10 * FS)
    t = np.linspace(0, 10, length)
    signal = (
        np.sin(2 * np.pi * 1.2 * t)
        + 0.5 * np.sin(2 * np.pi * 2.4 * t)
        + 0.1 * rng.standard_normal(length)
    )
    return signal, FS


def _load_single_record(record_path: str, lead: int, use_ptb: bool) -> tuple[np.ndarray, float]:
    if use_ptb:
        return _load_wfdb_single(record_path, lead)
    return _load_demo_single(record_path)


def load_ptb_dataset(data_dir: str,
                     n_subjects: int = N_SUBJECTS,
                     wavelet: str = "db4",
                     test_size: float = TEST_SIZE):
    """
    Load PTB records, preprocess, extract wavelet features, and split.

    If ``data_dir`` is a PhysioNet PTB tree (``patientXXX`` folders with *.hea files),
    real WFDB data is loaded. Otherwise the bundled demo placeholders are used.
    """

    raw_input = (data_dir or "").strip()

    use_real = False
    root = ""

    if raw_input and not _is_placeholder_data_path(raw_input):
        root = os.path.abspath(os.path.expanduser(raw_input))
        if not os.path.isdir(root):
            raise ValueError(f"Dataset path does not exist or is not a folder:\n{root}")
        if not _looks_like_ptbdb_root(root):
            raise ValueError(
                f"Folder does not look like PhysioNet PTB Diagnostic ({root}).\n"
                "Expect subfolders named patient<number>, each containing *.hea files."
            )
        use_real = True

    if use_real:
        subject_names, all_records = _collect_ptbdb_records(root, n_subjects)
    else:
        n = max(1, min(n_subjects, 5))
        subject_names = [f"Subject_{i + 1}" for i in range(n)]
        all_records = [(f"demo_{s}_{r}", s) for s in range(n) for r in range(6)]

    all_features = []
    all_labels = []
    raw_signals = {}

    for record_path, subject_id in all_records:
        signal, fs = _load_single_record(record_path, LEAD_INDEX, use_real)

        name = subject_names[subject_id]
        if name not in raw_signals:
            raw_signals[name] = (signal, fs)

        _, _, segments = preprocess_ecg(signal, fs)
        if len(segments) == 0:
            continue

        features = extract_features(segments, wavelet=wavelet)
        all_features.append(features)
        all_labels.extend([subject_id] * len(features))

    if not all_features:
        hint = ""
        if use_real:
            hint = (" Check records under " + root + " — preprocessing found no heartbeat "
                    "segments (try another lead_index in dataset_loader.LEAD_INDEX).")
        raise RuntimeError(f"No feature rows produced from dataset.{hint}")

    X = np.vstack(all_features)
    y = np.array(all_labels)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=test_size,
        random_state=RANDOM_STATE,
        stratify=y,
    )

    return X_train, X_test, y_train, y_test, subject_names, raw_signals
