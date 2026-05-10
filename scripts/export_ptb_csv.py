"""
Export one PTB Diagnostic ECG record to a single-column CSV file.

Example:
    python scripts/export_ptb_csv.py ^
        --root "D:\\path\\to\\physionet.org\\files\\ptbdb\\1.0.0" ^
        --patient patient001 ^
        --record s0010_re ^
        --lead 1 ^
        --output samples\\patient001_s0010_lead2.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import wfdb


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export a PTB ECG lead to CSV.")
    parser.add_argument("--root", required=True, help="PTBDB 1.0.0 root folder.")
    parser.add_argument("--patient", default="patient001", help="Patient folder name.")
    parser.add_argument("--record", default=None, help="Record name without .hea/.dat.")
    parser.add_argument("--lead", type=int, default=1, help="Zero-based lead index. 1 is Lead II in PTB.")
    parser.add_argument("--output", required=True, help="Output CSV path.")
    return parser.parse_args()


def first_record(patient_dir: Path) -> str:
    hea_files = sorted(patient_dir.glob("*.hea"))
    if not hea_files:
        raise FileNotFoundError(f"No .hea records found in {patient_dir}")
    return hea_files[0].stem


def main() -> None:
    args = parse_args()
    patient_dir = Path(args.root).expanduser().resolve() / args.patient
    record_name = args.record or first_record(patient_dir)
    record_path = patient_dir / record_name

    record = wfdb.rdrecord(str(record_path))
    if record.p_signal is None or record.p_signal.size == 0:
        raise ValueError(f"No signal samples found in {record_path}")
    if args.lead < 0 or args.lead >= record.p_signal.shape[1]:
        raise ValueError(f"Lead {args.lead} is out of range. Record has {record.p_signal.shape[1]} leads.")

    signal = record.p_signal[:, args.lead]
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savetxt(output, signal, delimiter=",", fmt="%.8f")

    duration = len(signal) / float(record.fs)
    print(f"Exported {len(signal)} samples from {args.patient}/{record_name}, lead {args.lead}.")
    print(f"Sampling rate: {record.fs:g} Hz, duration: {duration:.2f} s")
    print(f"CSV: {output}")


if __name__ == "__main__":
    main()
