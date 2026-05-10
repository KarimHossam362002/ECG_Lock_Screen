"""
classifiers.py
--------------
Three classifiers for ECG-based person identification:
    1. SVM   – Support Vector Machine  (RBF / Linear / Poly kernels)
    2. KNN   – K-Nearest Neighbours
    3. RF    – Random Forest

Each classifier is wrapped so it has a consistent interface:
    .train(X_train, y_train)
    .predict(X_test)  → labels
    .predict_proba(X_test)  → probabilities (for majority-vote)
    .accuracy(X_test, y_test)  → float
"""

from __future__ import annotations
import numpy as np
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score


# ── Base wrapper ──────────────────────────────────────────────

class BaseECGClassifier:
    name: str = "Base"

    def __init__(self):
        self.scaler = StandardScaler()
        self.model  = None

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
        # SVC with decision_function fallback
        d = self.model.decision_function(X_scaled)
        if d.ndim == 1:
            d = d.reshape(-1, 1)
        # Soft-max normalisation
        e = np.exp(d - d.max(axis=1, keepdims=True))
        return e / e.sum(axis=1, keepdims=True)

    def accuracy(self, X: np.ndarray, y: np.ndarray) -> float:
        return accuracy_score(y, self.predict(X))


# ── SVM ───────────────────────────────────────────────────────

class SVMClassifier(BaseECGClassifier):
    """
    Parameters tested:
        kernel : 'rbf', 'linear', 'poly'
        C      : regularisation (0.1, 1, 10, 100)
        gamma  : 'scale', 'auto'  (for RBF/Poly)
    """
    name = "SVM"

    def __init__(self, kernel: str = "rbf",
                 C: float = 10.0,
                 gamma: str = "scale"):
        super().__init__()
        self.params = dict(kernel=kernel, C=C, gamma=gamma)
        self.model = SVC(kernel=kernel, C=C, gamma=gamma,
                         probability=True, random_state=42,
                         decision_function_shape="ovr")

    def __repr__(self):
        return (f"SVM(kernel={self.params['kernel']}, "
                f"C={self.params['C']}, gamma={self.params['gamma']})")


SVM_PARAM_GRID = [
    dict(kernel="rbf",    C=1,   gamma="scale"),
    dict(kernel="rbf",    C=10,  gamma="scale"),
    dict(kernel="rbf",    C=100, gamma="scale"),
    dict(kernel="rbf",    C=10,  gamma="auto"),
    dict(kernel="linear", C=1),
    dict(kernel="linear", C=10),
    dict(kernel="poly",   C=1,   gamma="scale"),
]


# ── KNN ───────────────────────────────────────────────────────

class KNNClassifier(BaseECGClassifier):
    """
    Parameters tested:
        n_neighbors : 3, 5, 7, 11
        metric      : 'euclidean', 'manhattan'
    """
    name = "KNN"

    def __init__(self, n_neighbors: int = 5,
                 metric: str = "euclidean"):
        super().__init__()
        self.params = dict(n_neighbors=n_neighbors, metric=metric)
        self.model = KNeighborsClassifier(
            n_neighbors=n_neighbors, metric=metric
        )

    def __repr__(self):
        return (f"KNN(k={self.params['n_neighbors']}, "
                f"metric={self.params['metric']})")


KNN_PARAM_GRID = [
    dict(n_neighbors=3,  metric="euclidean"),
    dict(n_neighbors=5,  metric="euclidean"),
    dict(n_neighbors=7,  metric="euclidean"),
    dict(n_neighbors=11, metric="euclidean"),
    dict(n_neighbors=5,  metric="manhattan"),
]


# ── Random Forest ─────────────────────────────────────────────

class RFClassifier(BaseECGClassifier):
    """
    Parameters tested:
        n_estimators : 50, 100, 200
        max_depth    : None, 10, 20
    """
    name = "Random Forest"

    def __init__(self, n_estimators: int = 100,
                 max_depth=None):
        super().__init__()
        self.params = dict(n_estimators=n_estimators,
                           max_depth=max_depth)
        self.model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=42
        )

    def __repr__(self):
        return (f"RF(n={self.params['n_estimators']}, "
                f"depth={self.params['max_depth']})")


RF_PARAM_GRID = [
    dict(n_estimators=50,  max_depth=None),
    dict(n_estimators=100, max_depth=None),
    dict(n_estimators=200, max_depth=None),
    dict(n_estimators=100, max_depth=10),
    dict(n_estimators=100, max_depth=20),
]


# ── Majority-vote identification ──────────────────────────────

THRESHOLD = 0.80   # 80% of heartbeats must agree → identified


def identify_subject(classifier: BaseECGClassifier,
                     segments: np.ndarray,
                     subject_labels: list[str]) -> tuple[str, float]:
    """
    Identify a subject from their ECG heartbeat segments.

    Returns
    -------
    identity   : str  – predicted subject name, or "Unidentified"
    confidence : float  – fraction of beats agreeing
    """
    if len(segments) == 0:
        return "Unidentified", 0.0

    predictions = classifier.predict(segments)
    # Count votes
    unique, counts = np.unique(predictions, return_counts=True)
    best_idx  = np.argmax(counts)
    best_label = unique[best_idx]
    confidence = counts[best_idx] / len(predictions)

    if confidence >= THRESHOLD:
        # Map numeric label → subject name
        try:
            idx = int(best_label)
            name = subject_labels[idx] if idx < len(subject_labels) else str(best_label)
        except (ValueError, IndexError):
            name = str(best_label)
        return name, confidence
    return "Unidentified", confidence
