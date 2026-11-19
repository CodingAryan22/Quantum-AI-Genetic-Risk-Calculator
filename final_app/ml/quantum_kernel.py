"""
Quantum kernel built with Qiskit.

Each patient's 10 features are loaded into a 10-qubit circuit with Qiskit's ZZ
feature map (one qubit per feature, entangling ZZ rotations between every
pair, repeated twice). The kernel between two patients is the fidelity of
their quantum states:

    k(x, y) = |<psi(x) | psi(y)>|^2

A classical support vector machine then uses this kernel (a "quantum kernel
SVM", the same model as Qiskit Machine Learning's QSVC).

The circuits are simulated exactly with Qiskit's Statevector. Each patient's
state is computed once (2^10 = 1,024 amplitudes), so the whole kernel matrix is
one matrix product instead of n^2 separate circuit runs.
"""

import numpy as np
from qiskit.circuit.library import zz_feature_map
from qiskit.quantum_info import Statevector
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.svm import SVC

REPS = 2
ENTANGLEMENT = "full"


def feature_map(num_features: int):
    return zz_feature_map(num_features, reps=REPS, entanglement=ENTANGLEMENT)


def statevectors(X_angles: np.ndarray) -> np.ndarray:
    """
    Simulates the feature-map circuit for every row of X_angles (features
    already scaled to rotation angles). Returns an (n, 2^d) complex array.
    """
    X_angles = np.atleast_2d(X_angles)
    circuit = feature_map(X_angles.shape[1])
    states = [Statevector(circuit.assign_parameters(x)).data for x in X_angles]
    return np.asarray(states, dtype=np.complex128)


def fidelity_kernel(states_a: np.ndarray, states_b: np.ndarray) -> np.ndarray:
    """Kernel matrix K[i, j] = |<a_i|b_j>|^2."""
    return np.abs(states_a.conj() @ states_b.T) ** 2


def circuit_summary(num_features: int) -> dict:
    """Size of the circuit, for the report and the model comparison page."""
    circuit = feature_map(num_features).decompose()
    return {
        "qubits": num_features,
        "feature_map": f"ZZ feature map, {ENTANGLEMENT} entanglement, {REPS} repetitions",
        "kernel": "state fidelity |<psi(x)|psi(y)>|^2, exact statevector simulation",
        "depth": circuit.depth(),
        "gate_counts": {k: int(v) for k, v in circuit.count_ops().items()},
    }


class QuantumKernelSVM(BaseEstimator, ClassifierMixin):
    """
    Support vector machine on the quantum fidelity kernel (scikit-learn API).

    scale : features are min-max scaled to [0, pi * scale] before encoding.
            Smaller values keep states closer together (a smoother kernel).
    C     : SVM regularisation strength.
    """

    def __init__(self, scale: float = 1.0, C: float = 1.0, random_state: int = 0):
        self.scale = scale
        self.C = C
        self.random_state = random_state

    def _angles(self, X):
        span = np.where(self.x_max_ > self.x_min_, self.x_max_ - self.x_min_, 1.0)
        return np.clip((np.asarray(X, float) - self.x_min_) / span, 0.0, 1.0) * np.pi * self.scale

    def fit(self, X, y, states=None):
        X = np.asarray(X, float)
        self.x_min_, self.x_max_ = X.min(axis=0), X.max(axis=0)
        # `states` lets the training script reuse already-simulated circuits.
        states = statevectors(self._angles(X)) if states is None else states
        # complex64 halves the saved model size; the precision loss is ~1e-7.
        self.train_states_ = states.astype(np.complex64)
        self.svc_ = SVC(kernel="precomputed", C=self.C, probability=True,
                        random_state=self.random_state)
        self.svc_.fit(fidelity_kernel(states, states), y)
        self.classes_ = self.svc_.classes_
        self.n_features_in_ = X.shape[1]
        return self

    def kernel_to_train(self, X):
        return fidelity_kernel(statevectors(self._angles(X)), self.train_states_)

    def predict_proba(self, X):
        return self.svc_.predict_proba(self.kernel_to_train(X))

    def decision_function(self, X):
        return self.svc_.decision_function(self.kernel_to_train(X))

    def predict(self, X):
        return self.svc_.predict(self.kernel_to_train(X))
