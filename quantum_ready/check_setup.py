"""
Checks that the quantum toolchain is installed and working.

    python check_setup.py            # offline checks
    python check_setup.py --online   # also connects to IBM Quantum and lists devices
"""

import argparse
import importlib.metadata as md
import os
import platform
import sys

import qready  # noqa: F401  (applies the Aer import fix)

PACKAGES = ["qiskit", "qiskit-aer", "qiskit-ibm-runtime", "scikit-learn", "numpy", "pandas"]


def ok(msg):
    print(f"  [OK]   {msg}")


def bad(msg):
    print(f"  [--]   {msg}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--online", action="store_true", help="connect to IBM Quantum")
    args = p.parse_args()
    ready = True

    print(f"\nPython {platform.python_version()} ({sys.executable})\n\n1. Libraries")
    for name in PACKAGES:
        try:
            ok(f"{name} {md.version(name)}")
        except md.PackageNotFoundError:
            bad(f"{name} not installed  ->  pip install -r requirements.txt")
            ready = False

    print("\n2. Local simulator (Qiskit Aer)")
    try:
        from qiskit import QuantumCircuit, transpile
        from qiskit_aer import AerSimulator

        bell = QuantumCircuit(2)
        bell.h(0)
        bell.cx(0, 1)
        bell.measure_all()
        sim = AerSimulator()
        counts = sim.run(transpile(bell, sim), shots=2000, seed_simulator=1).result().get_counts()
        share = (counts.get("00", 0) + counts.get("11", 0)) / 2000
        ok(f"Bell-state test: {counts}  ({share:.0%} correlated, expected 100%)")
    except Exception as exc:
        bad(f"Aer simulator failed: {exc}")
        ready = False

    print("\n3. Real-device noise model")
    try:
        from qready.backends import DEFAULT_FAKE, fake_backend

        dev = fake_backend(DEFAULT_FAKE)
        ok(f"{dev.name}: {dev.num_qubits} qubits, native gates "
           f"{sorted(g for g in dev.operation_names if g not in {'measure', 'delay', 'reset', 'for_loop', 'if_else', 'switch_case', 'while_loop'})}")
    except Exception as exc:
        bad(f"Fake backend failed: {exc}")
        ready = False

    print("\n4. Project circuit")
    try:
        from qready.circuits import circuit_stats, kernel_circuit

        s = circuit_stats(kernel_circuit().decompose(reps=2))
        ok(f"Fidelity kernel circuit: {s['qubits']} qubits, depth {s['depth']}, "
           f"{s['two_qubit_gates']} two-qubit gates")
    except Exception as exc:
        bad(f"Circuit build failed: {exc}")
        ready = False

    print("\n5. IBM Quantum account (for real hardware)")
    hardware = False
    try:
        from qiskit_ibm_runtime import QiskitRuntimeService

        saved = QiskitRuntimeService.saved_accounts()
        if saved or os.environ.get("QISKIT_IBM_TOKEN"):
            ok("Credentials found (" + ("saved account" if saved else "QISKIT_IBM_TOKEN") + ")")
            hardware = True
        else:
            bad("No IBM Quantum API key yet. Real hardware runs need one: run "
                "`python ibm_login.py` (free account at quantum.cloud.ibm.com)")
    except Exception as exc:
        bad(f"Could not check credentials: {exc}")

    if args.online and hardware:
        try:
            from qready.backends import runtime_service

            service = runtime_service()
            devices = service.backends(operational=True, simulator=False, min_num_qubits=9)
            ok("Devices: " + ", ".join(f"{b.name} ({b.num_qubits}q, "
                                       f"{b.status().pending_jobs} queued)" for b in devices))
        except Exception as exc:
            bad(f"Connection failed: {exc}")
            hardware = False

    print("\nSummary")
    print(f"  Simulation (ideal + real-device noise): {'READY' if ready else 'NOT READY'}")
    print(f"  Real IBM hardware:                      "
          f"{'READY' if ready and hardware else 'code ready, needs an IBM Quantum API key'}\n")
    return 0 if ready else 1


if __name__ == "__main__":
    sys.exit(main())
