"""
The quantum circuits.

Feature map: Qiskit's ZZ feature map, one qubit per patient feature (10 qubits),
the same circuit the web app's quantum kernel SVM uses.

Kernel circuit: to measure the similarity of two patients x and y on real
hardware we cannot read out the state vector. Instead we run

    |0...0>  --U(x)--  U(y)^dagger  --  measure all qubits

and count how often every qubit reads 0. That probability is exactly

    P(0...0) = |<0| U(y)^dagger U(x) |0>|^2 = |<psi(y)|psi(x)>|^2 = k(x, y)

(the "compute-uncompute" or fidelity test). With a finite number of shots it
is an estimate, and on noisy hardware it is biased downwards.
"""

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import zz_feature_map
from qiskit.quantum_info import Statevector

from .data import FEATURES

NUM_FEATURES = len(FEATURES)
REPS = 2
ENTANGLEMENT = "full"


def feature_map(num_qubits=NUM_FEATURES, reps=REPS, entanglement=ENTANGLEMENT, prefix="x"):
    return zz_feature_map(num_qubits, reps=reps, entanglement=entanglement, parameter_prefix=prefix)


def kernel_circuit(num_qubits=NUM_FEATURES, reps=REPS, entanglement=ENTANGLEMENT) -> QuantumCircuit:
    """U(x) followed by U(y)^dagger, measured. Parameters: x[0..n-1], y[0..n-1]."""
    u_x = feature_map(num_qubits, reps, entanglement, "x")
    u_y = feature_map(num_qubits, reps, entanglement, "y")
    qc = QuantumCircuit(num_qubits, name="fidelity_kernel")
    qc.compose(u_x, inplace=True)
    qc.compose(u_y.inverse(), inplace=True)
    qc.measure_all()
    return qc


def parameter_columns(circuit: QuantumCircuit) -> list[tuple[str, int]]:
    """For each circuit parameter, in the order the primitives expect: ('x' or 'y', feature index)."""
    return [(p.vector.name, p.index) for p in circuit.parameters]


def bind_pairs(circuit: QuantumCircuit, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    """Parameter values, shape (pairs, n_params), for running the circuit on pairs (xs[i], ys[i])."""
    cols = parameter_columns(circuit)
    out = np.empty((len(xs), len(cols)))
    for j, (name, idx) in enumerate(cols):
        out[:, j] = (xs if name == "x" else ys)[:, idx]
    return out


def statevectors(X_angles: np.ndarray, reps=REPS, entanglement=ENTANGLEMENT) -> np.ndarray:
    """Exact simulation: the feature-map state of every row (what the web app does)."""
    X_angles = np.atleast_2d(X_angles)
    fmap = feature_map(X_angles.shape[1], reps, entanglement)
    return np.asarray([Statevector(fmap.assign_parameters(x)).data for x in X_angles])


def circuit_stats(circuit: QuantumCircuit) -> dict:
    ops = circuit.count_ops()
    two_qubit = sum(int(v) for k, v in ops.items() if k in {"cx", "cz", "ecr", "rzz", "swap"})
    return {
        "qubits": circuit.num_qubits,
        "depth": circuit.depth(),
        "two_qubit_gates": two_qubit,
        "gate_counts": {k: int(v) for k, v in ops.items()},
    }
