"""
qready: the RiskPredict quantum kernel, ready to run on simulators and IBM Quantum hardware.

Kept separate from final_app on purpose: the web app uses exact statevector
simulation (fast, deterministic), while this package runs the same circuits
the way a quantum computer would: as measured shots on a backend.
"""

from . import _aer_fix  # noqa: F401  (must run before anything imports qiskit_aer)
