"""
Where the circuits run.

    exact  - statevector maths, no shots, no noise (what the web app uses)
    ideal  - Qiskit Aer simulator: real shot sampling, perfect qubits
    noisy  - Qiskit Aer with the noise model, qubit layout and native gates of a
             real IBM processor (a "fake backend" built from calibration data)
    ibm    - a real IBM Quantum computer through Qiskit Runtime (needs an
             IBM Quantum account; see ibm_login.py)

The same transpile-and-sample code path is used for ideal, noisy and ibm, so
moving to hardware changes only which backend object is passed in.
"""

import os

from . import _aer_fix  # noqa: F401

BACKENDS = ("exact", "ideal", "noisy", "ibm")
DEFAULT_FAKE = "FakeTorino"  # 133-qubit IBM Heron processor
IBM_CHANNEL = "ibm_quantum_platform"
MIN_QUBITS = 9


class HardwareUnavailable(RuntimeError):
    """No IBM Quantum account is set up, or no device could be reached."""


def fake_backend(name: str = DEFAULT_FAKE):
    from qiskit_ibm_runtime import fake_provider

    try:
        return getattr(fake_provider, name)()
    except AttributeError:
        names = sorted(n for n in dir(fake_provider) if n.startswith("Fake") and n[4:5].isupper())
        raise ValueError(f"Unknown fake backend {name!r}. Options include: {', '.join(names[:12])} ...")


def runtime_service():
    """Connects to IBM Quantum with the saved account, or QISKIT_IBM_TOKEN if it is set."""
    try:
        from qiskit_ibm_runtime import QiskitRuntimeService
    except ImportError as exc:
        raise HardwareUnavailable("qiskit-ibm-runtime is not installed.") from exc

    token = os.environ.get("QISKIT_IBM_TOKEN")
    instance = os.environ.get("QISKIT_IBM_INSTANCE") or None
    try:
        if token:
            return QiskitRuntimeService(channel=IBM_CHANNEL, token=token, instance=instance)
        return QiskitRuntimeService(instance=instance)  # uses the account saved by ibm_login.py
    except Exception as exc:
        raise HardwareUnavailable(
            "Could not connect to IBM Quantum. Run `python ibm_login.py` once to save your "
            f"API key, or set QISKIT_IBM_TOKEN. ({type(exc).__name__}: {exc})"
        ) from exc


def get_backend(kind: str, fake: str = DEFAULT_FAKE, ibm_backend: str | None = None):
    """Returns the backend object for `kind` (None for exact)."""
    if kind not in BACKENDS:
        raise ValueError(f"backend must be one of {BACKENDS}")
    if kind == "exact":
        return None
    if kind == "ideal":
        from qiskit_aer import AerSimulator

        return AerSimulator()
    if kind == "noisy":
        from qiskit_aer import AerSimulator

        return AerSimulator.from_backend(fake_backend(fake))
    service = runtime_service()
    try:
        if ibm_backend:
            return service.backend(ibm_backend)
        return service.least_busy(operational=True, simulator=False, min_num_qubits=MIN_QUBITS)
    except Exception as exc:
        raise HardwareUnavailable(f"No IBM Quantum device available: {exc}") from exc


def get_sampler(kind: str, backend):
    """A SamplerV2 primitive for the backend. Real hardware gets error suppression switched on."""
    if kind == "ibm":
        from qiskit_ibm_runtime import SamplerV2

        sampler = SamplerV2(mode=backend)
        sampler.options.dynamical_decoupling.enable = True   # protects idle qubits
        sampler.options.twirling.enable_gates = True          # turns coherent errors into random noise
        return sampler
    from qiskit.primitives import BackendSamplerV2

    return BackendSamplerV2(backend=backend)


def describe(kind: str, backend) -> str:
    if backend is None:
        return "exact statevector simulation"
    name = getattr(backend, "name", type(backend).__name__)
    if callable(name):
        name = name()
    return {"ideal": f"Aer simulator ({name}), ideal qubits",
            "noisy": f"Aer simulator with real-device noise ({name})",
            "ibm": f"IBM Quantum hardware: {name}"}[kind]
