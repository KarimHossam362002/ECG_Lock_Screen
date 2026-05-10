"""
training_engine.py
------------------
Orchestrates training, parameter search, and result collection
for all three classifiers across all three wavelets.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from ml.classifiers import (
    BaseECGClassifier,
    KNNClassifier,
    KNN_PARAM_GRID,
    RFClassifier,
    RF_PARAM_GRID,
    SVMClassifier,
    SVM_PARAM_GRID,
    identify_subject,
)
from ml.ecg_preprocessing import preprocess_ecg
from ml.feature_extraction import WAVELETS


@dataclass
class ClassifierResult:
    classifier_name: str
    params: dict
    wavelet: str
    train_acc: float
    test_acc: float
    model: BaseECGClassifier = field(repr=False)


@dataclass
class TrainingResults:
    results: list[ClassifierResult] = field(default_factory=list)
    best_per_classifier: dict = field(default_factory=dict)
    best_overall: ClassifierResult | None = None
    subject_names: list[str] = field(default_factory=list)


def _classifier_configs():
    return (
        [("SVM", SVMClassifier, p) for p in SVM_PARAM_GRID]
        + [("KNN", KNNClassifier, p) for p in KNN_PARAM_GRID]
        + [("Random Forest", RFClassifier, p) for p in RF_PARAM_GRID]
    )


def train_all(
    X_train,
    X_test,
    y_train,
    y_test,
    subject_names: list[str],
    progress_cb: Callable[[str, int, int], None] | None = None,
    wavelet: str = "db4",
    step_offset: int = 0,
    total_steps: int | None = None,
) -> TrainingResults:
    """
    Train all classifiers with all parameter combinations for one wavelet.

    progress_cb(message, current_step, total_steps)
    """
    results_obj = TrainingResults(subject_names=subject_names)
    all_configs = _classifier_configs()
    total = len(all_configs) if total_steps is None else total_steps
    best_per: dict[str, ClassifierResult] = {}

    for step, (name, cls_type, params) in enumerate(all_configs):
        if progress_cb:
            progress_cb(
                f"Training {name} ({wavelet}) - {params}",
                step_offset + step,
                total,
            )

        clf = cls_type(**params)
        try:
            clf.train(X_train, y_train)
            train_acc = clf.accuracy(X_train, y_train)
            test_acc = clf.accuracy(X_test, y_test)
        except Exception:
            train_acc = 0.0
            test_acc = 0.0

        result = ClassifierResult(
            classifier_name=name,
            params=params,
            wavelet=wavelet,
            train_acc=train_acc,
            test_acc=test_acc,
            model=clf,
        )
        results_obj.results.append(result)

        if name not in best_per or test_acc > best_per[name].test_acc:
            best_per[name] = result

    results_obj.best_per_classifier = best_per
    if best_per:
        results_obj.best_overall = max(best_per.values(), key=lambda r: r.test_acc)

    if progress_cb:
        progress_cb(
            f"Training complete for {wavelet}.",
            step_offset + len(all_configs),
            total,
        )

    return results_obj


def train_wavelet_comparison(
    datasets_by_wavelet: dict[str, tuple],
    subject_names: list[str],
    progress_cb: Callable[[str, int, int], None] | None = None,
) -> TrainingResults:
    """
    Train every classifier/parameter combination for db1, db2, and db4.

    datasets_by_wavelet maps a wavelet name to:
        (X_train, X_test, y_train, y_test)
    """
    ordered_wavelets = [w for w in WAVELETS if w in datasets_by_wavelet]
    if not ordered_wavelets:
        raise ValueError("No wavelet datasets were provided for training.")

    configs_per_wavelet = len(_classifier_configs())
    total_steps = configs_per_wavelet * len(ordered_wavelets)

    combined = TrainingResults(subject_names=subject_names)
    step_offset = 0

    for wavelet in ordered_wavelets:
        X_train, X_test, y_train, y_test = datasets_by_wavelet[wavelet]
        partial = train_all(
            X_train,
            X_test,
            y_train,
            y_test,
            subject_names,
            progress_cb=progress_cb,
            wavelet=wavelet,
            step_offset=step_offset,
            total_steps=total_steps,
        )
        combined.results.extend(partial.results)
        step_offset += configs_per_wavelet

    for result in combined.results:
        best = combined.best_per_classifier.get(result.classifier_name)
        if best is None or result.test_acc > best.test_acc:
            combined.best_per_classifier[result.classifier_name] = result

    if combined.results:
        combined.best_overall = max(combined.results, key=lambda r: r.test_acc)

    if progress_cb:
        progress_cb("Training complete!", total_steps, total_steps)

    return combined


def run_identification(
    best_result: ClassifierResult,
    raw_signal: np.ndarray,
    fs: float,
    subject_names: list[str],
) -> tuple[str, float]:
    """
    Given a raw ECG signal, run the best trained classifier
    and return the identified subject name + confidence.
    """
    _, _, segments = preprocess_ecg(raw_signal, fs)
    from ml.feature_extraction import extract_features

    wavelet = best_result.wavelet if best_result.wavelet in WAVELETS else "db4"
    features = extract_features(segments, wavelet=wavelet)
    if len(features) == 0:
        return "Unidentified", 0.0
    return identify_subject(best_result.model, features, subject_names)
