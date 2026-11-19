"""
Checks for the hardware-ready quantum kernel.  Run from quantum_ready/:
    python -m pytest -q tests
"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from qiskit.quantum_info import Statevector  # noqa: E402

from qready import backends, circuits, data  # noqa: E402
from qready.kernel import QuantumKernel  # noqa: E402

RNG = np.random.default_rng(0)
ANGLES = RNG.uniform(0, 0.4, size=(6, circuits.NUM_FEATURES))


def test_kernel_circuit_measures_the_fidelity():
    """P(0...0) of U(x) U(y)^dagger equals |<psi(y)|psi(x)>|^2, with parameters bound correctly."""
    qc = circuits.kernel_circuit().remove_final_measurements(inplace=False)
    x, y = ANGLES[0], ANGLES[1]
    bound = qc.assign_parameters(circuits.bind_pairs(qc, x[None], y[None])[0])
    p_zero = abs(Statevector(bound).data[0]) ** 2
    sx, sy = circuits.statevectors(np.vstack([x, y]))
    assert p_zero == pytest.approx(abs(np.vdot(sy, sx)) ** 2, abs=1e-10)


def test_exact_kernel_matches_web_app():
    sys.path.insert(0, str(data.ROOT / "final_app"))
    from ml.quantum_kernel import fidelity_kernel, statevectors

    app = fidelity_kernel(statevectors(ANGLES), statevectors(ANGLES))
    ours = QuantumKernel("exact").matrix(ANGLES)
    assert np.allclose(app, ours, atol=1e-6)


def test_ideal_simulator_estimates_the_exact_kernel():
    exact = QuantumKernel("exact").matrix(ANGLES[:4], ANGLES[4:])
    sampled = QuantumKernel("ideal", shots=8000, seed=1).matrix(ANGLES[:4], ANGLES[4:])
    assert np.abs(sampled - exact).max() < 0.03


def test_symmetric_matrix_has_unit_diagonal():
    K = QuantumKernel("ideal", shots=500, seed=1).matrix(ANGLES[:4])
    assert np.allclose(np.diag(K), 1) and np.allclose(K, K.T)


def test_noisy_backend_uses_device_gates_and_mitigation_helps():
    pair = (ANGLES[:3], ANGLES[3:5])
    exact = QuantumKernel("exact", entanglement="linear").matrix(*pair)
    raw = QuantumKernel("noisy", shots=4000, entanglement="linear", seed=1)
    fixed = QuantumKernel("noisy", shots=4000, entanglement="linear", seed=1, mitigate=True)
    assert set(raw.report()["device_circuit"]["gate_counts"]) <= {"cz", "rz", "sx", "x", "measure",
                                                                 "barrier"}
    err_raw = np.abs(raw.matrix(*pair) - exact).mean()
    err_fixed = np.abs(fixed.matrix(*pair) - exact).mean()
    assert err_fixed < err_raw


def test_hardware_without_account_fails_clearly(monkeypatch):
    monkeypatch.delenv("QISKIT_IBM_TOKEN", raising=False)
    from qiskit_ibm_runtime import QiskitRuntimeService

    if QiskitRuntimeService.saved_accounts():
        pytest.skip("an IBM Quantum account is saved on this machine")
    with pytest.raises(backends.HardwareUnavailable):
        backends.get_backend("ibm")


def test_sample_is_stratified():
    df = data.load_cohort()
    Xtr, ytr, Xte, yte = data.sample(df, 30, 30, seed=3)
    assert len(Xtr) == len(Xte) == 30 and ytr.sum() >= 2 and yte.sum() >= 2
