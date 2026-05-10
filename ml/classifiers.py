"""
classifiers.py
--------------
Classifier wrappers and ECG identity decision logic.
"""

from __future__ import annotations

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


class BaseECGClassifier:
    name: str = "Base"

    def __init__(self):
        self.scaler = StandardScaler()
        self.model = None

    def train(self, X: np.ndarray, y: np.ndarray) -> None:
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)

    def predict(self, X: np.ndarray) -> np.ndarray:
        X_scaled = self.scaler.transform(X)
        return self.model.predict(X_scaled)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        X_scaled = self.scaler.transform(X)
        if hasattr(self.model, "predict_proba"):
            return self.model.predict_proba(X_scaled)
        d = self.model.decision_function(X_scaled)
        if d.ndim == 1:
            d = d.reshape(-1, 1)
        e = np.exp(d - d.max(axis=1, keepdims=True))
        return e / e.sum(axis=1, keepdims=True)

    def accuracy(self, X: np.ndarray, y: np.ndarray) -> float:
        return accuracy_score(y, self.predict(X))


class SVMClassifier(BaseECGClassifier):
    name = "SVM"

    def __init__(self, kernel: str = "rbf", C: float = 10.0, gamma: str = "scale"):
        super().__init__()
        self.params = dict(kernel=kernel, C=C, gamma=gamma)
        self.model = SVC(
            kernel=kernel,
            C=C,
            gamma=gamma,
            probability=True,
            random_state=42,
            decision_function_shape="ovr",
        )

    def __repr__(self):
        return f"SVM(kernel={self.params['kernel']}, C={self.params['C']}, gamma={self.params['gamma']})"


SVM_PARAM_GRID = [
    dict(kernel="rbf", C=1, gamma="scale"),
    dict(kernel="rbf", C=10, gamma="scale"),
    dict(kernel="rbf", C=100, gamma="scale"),
    dict(kernel="rbf", C=10, gamma="auto"),
    dict(kernel="linear", C=1),
    dict(kernel="linear", C=10),
    dict(kernel="poly", C=1, gamma="scale"),
]


class KNNClassifier(BaseECGClassifier):
    name = "KNN"

    def __init__(self, n_neighbors: int = 5, metric: str = "euclidean"):
        super().__init__()
        self.params = dict(n_neighbors=n_neighbors, metric=metric)
        self.model = KNeighborsClassifier(n_neighbors=n_neighbors, metric=metric)

    def __repr__(self):
        return f"KNN(k={self.params['n_neighbors']}, metric={self.params['metric']})"


KNN_PARAM_GRID = [
    dict(n_neighbors=3, metric="euclidean"),
    dict(n_neighbors=5, metric="euclidean"),
    dict(n_neighbors=7, metric="euclidean"),
    dict(n_neighbors=11, metric="euclidean"),
    dict(n_neighbors=5, metric="manhattan"),
]


class RFClassifier(BaseECGClassifier):
    name = "Random Forest"

    def __init__(self, n_estimators: int = 100, max_depth=None):
        super().__init__()
        self.params = dict(n_estimators=n_estimators, max_depth=max_depth)
        self.model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=42,
        )

    def __repr__(self):
        return f"RF(n={self.params['n_estimators']}, depth={self.params['max_depth']})"


RF_PARAM_GRID = [
    dict(n_estimators=50, max_depth=None),
    dict(n_estimators=100, max_depth=None),
    dict(n_estimators=200, max_depth=None),
    dict(n_estimators=100, max_depth=10),
    dict(n_estimators=100, max_depth=20),
]


THRESHOLD = 0.80
OPEN_SET_THRESHOLD = 0.80
OPEN_SET_PERCENTILE = 99.0
OPEN_SET_MARGIN = 1.15


def fit_open_set_rejection(
    classifier: BaseECGClassifier,
    X_train: np.ndarray,
    y_train: np.ndarray,
) -> None:
    """Store per-class centroids and distance limits for unknown-person rejection."""
    X_scaled = classifier.scaler.transform(X_train)
    centroids = {}
    limits = {}

    for label in np.unique(y_train):
        class_rows = X_scaled[y_train == label]
        centroid = class_rows.mean(axis=0)
        distances = np.linalg.norm(class_rows - centroid, axis=1)
        limit = np.percentile(distances, OPEN_SET_PERCENTILE) * OPEN_SET_MARGIN
        centroids[int(label)] = centroid
        limits[int(label)] = max(float(limit), 1e-9)

    classifier.open_set_centroids = centroids
    classifier.open_set_limits = limits


def _known_vote_fraction(
    classifier: BaseECGClassifier,
    features: np.ndarray,
    predicted_label,
) -> float:
    centroids = getattr(classifier, "open_set_centroids", None)
    limits = getattr(classifier, "open_set_limits", None)
    if not centroids or not limits:
        return 1.0

    try:
        label = int(predicted_label)
    except (TypeError, ValueError):
        return 0.0
    if label not in centroids or label not in limits:
        return 0.0

    X_scaled = classifier.scaler.transform(features)
    distances = np.linalg.norm(X_scaled - centroids[label], axis=1)
    return float(np.mean(distances <= limits[label]))


def identify_subject(
    classifier: BaseECGClassifier,
    segments: np.ndarray,
    subject_labels: list[str],
) -> tuple[str, float]:
    """
    Identify a subject from heartbeat feature rows.

    A subject is accepted only if:
    1. At least 80% of beats vote for the same class.
    2. At least 80% of beats are close enough to that class's trained feature cluster.
    """
    if len(segments) == 0:
        return "Unidentified", 0.0

    predictions = classifier.predict(segments)
    unique, counts = np.unique(predictions, return_counts=True)
    best_idx = np.argmax(counts)
    best_label = unique[best_idx]
    vote_confidence = counts[best_idx] / len(predictions)

    if vote_confidence < THRESHOLD:
        return "Unidentified", float(vote_confidence)

    known_fraction = _known_vote_fraction(classifier, segments, best_label)
    if known_fraction < OPEN_SET_THRESHOLD:
        return "Unidentified", float(min(vote_confidence, known_fraction))

    try:
        idx = int(best_label)
        name = subject_labels[idx] if idx < len(subject_labels) else str(best_label)
    except (ValueError, IndexError):
        name = str(best_label)
    return name, float(min(vote_confidence, known_fraction))
