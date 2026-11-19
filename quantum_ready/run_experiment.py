"""
Runs the RiskPredict quantum kernel SVM on a chosen backend and compares it
with the exact (noise-free) answer.

Examples (run from the quantum_ready folder):
    python run_experiment.py --backend ideal
    python run_experiment.py --backend noisy                 # real-device noise, simulated
    python run_experiment.py --backend ibm --dry-run         # what a hardware run would need
    python run_experiment.py --backend ibm --train 20 --test 10 --shots 1000

For each backend it:
  1. picks a small stratified set of synthetic patients (train / test),
  2. scales their 9 features to rotation angles exactly as the web app does,
  3. measures the quantum kernel (patient similarity) with fidelity circuits,
  4. trains an SVM on that kernel and scores the test patients (AUC),
  5. repeats 3-4 with the exact kernel, and reports how far the backend is off.
Results are saved to results/<backend>-<time>.json.
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score
from sklearn.svm import SVC

from qready import backends, data
from qready.kernel import QuantumKernel

RESULTS_DIR = Path(__file__).resolve().parent / "results"
SMALL_SAMPLE_SCALE = 0.02


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--backend", choices=backends.BACKENDS, default="ideal")
    p.add_argument("--train", type=int, default=40, help="training patients")
    p.add_argument("--test", type=int, default=40, help="test patients")
    p.add_argument("--shots", type=int, default=2000)
    p.add_argument("--reps", type=int, default=2, help="feature-map repetitions (app: 2)")
    p.add_argument("--entanglement", default="full", choices=["full", "linear", "circular"],
                   help="app: full. linear needs far fewer two-qubit gates on hardware")
    p.add_argument("--scale", type=float, default=SMALL_SAMPLE_SCALE,
                   help="angle scale. The app uses 0.1 (tuned on 1,500 patients); with tens "
                        "of patients a smaller scale gives a smoother, more useful kernel")
    p.add_argument("--C", type=float, default=1.0, help="SVM regularisation")
    p.add_argument("--fake", default=backends.DEFAULT_FAKE, help="device whose noise to copy")
    p.add_argument("--ibm-backend", default=None, help="IBM device name (default: least busy)")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--no-mitigation", action="store_true",
                   help="turn off the depolarising-noise correction (on by default for noisy/ibm)")
    p.add_argument("--dry-run", action="store_true",
                   help="only transpile for the device and print what the run would need")
    p.add_argument("--no-save", action="store_true")
    return p.parse_args(argv)


def svm_auc(K_train, y_train, K_test, y_test, C):
    svm = SVC(kernel="precomputed", C=C, class_weight="balanced").fit(K_train, y_train)
    return float(roc_auc_score(y_test, svm.decision_function(K_test)))


def main(argv=None):
    args = parse_args(argv)
    scale = args.scale
    df = data.load_cohort()
    X_tr, y_tr, X_te, y_te = data.sample(df, args.train, args.test, seed=args.seed)
    scaler = data.AngleScaler(scale).fit(X_tr)
    A_tr, A_te = scaler.transform(X_tr), scaler.transform(X_te)

    try:
        qk = QuantumKernel(args.backend, shots=args.shots, reps=args.reps,
                           entanglement=args.entanglement, fake=args.fake,
                           ibm_backend=args.ibm_backend, seed=args.seed,
                           mitigate=args.backend in ("noisy", "ibm") and not args.no_mitigation)
    except backends.HardwareUnavailable as exc:
        print(f"\nHardware not available: {exc}\n")
        print("Everything else is ready. Try `--backend noisy` to simulate the same run with "
              "real-device noise.")
        return 2

    # Test patients' self-overlaps are counted in the second term; training ones in the first.
    n_circuits = qk.circuits_needed(len(A_tr)) + qk.circuits_needed(len(A_te), len(A_tr))
    info = qk.report()
    print(f"\nBackend : {info['backend']}")
    print(f"Patients: {len(A_tr)} train ({y_tr.sum()} positive), "
          f"{len(A_te)} test ({y_te.sum()} positive); angle scale {scale}")
    lc = info["logical_circuit"]
    print(f"Circuit : {lc['qubits']} qubits, depth {lc['depth']}, "
          f"{lc['two_qubit_gates']} two-qubit gates (ZZ map, {args.entanglement}, reps {args.reps})")
    if "device_circuit" in info:
        dc = info["device_circuit"]
        print(f"On device: depth {dc['depth']}, {dc['two_qubit_gates']} two-qubit gates, "
              f"gates {dc['gate_counts']}")
        if "physical_qubits" in info:
            print(f"Physical qubits: {info['physical_qubits']}")
        print(f"Workload: {n_circuits} circuits x {args.shots} shots "
              f"= {n_circuits * args.shots:,} shots")

    if args.dry_run:
        print("\nDry run: nothing was executed.")
        return 0

    t0 = time.perf_counter()
    exact = QuantumKernel("exact", reps=args.reps, entanglement=args.entanglement)
    Ke_tr, Ke_te = exact.matrix(A_tr), exact.matrix(A_te, A_tr)
    exact_auc = svm_auc(Ke_tr, y_tr, Ke_te, y_te, args.C)
    exact_s = time.perf_counter() - t0

    result = {"exact_auc": exact_auc, "exact_seconds": round(exact_s, 3)}
    if args.backend != "exact":
        print("\nRunning circuits ...", flush=True)
        K_tr, K_te = qk.matrix(A_tr), qk.matrix(A_te, A_tr)
        off = ~np.eye(len(K_tr), dtype=bool)
        result.update({
            "backend_auc": svm_auc(K_tr, y_tr, K_te, y_te, args.C),
            "kernel_mean_abs_error": float(np.mean(np.abs(np.r_[K_tr[off] - Ke_tr[off],
                                                                (K_te - Ke_te).ravel()]))),
            "mean_kernel_exact": float(np.r_[Ke_tr[off], Ke_te.ravel()].mean()),
            "mean_kernel_backend": float(np.r_[K_tr[off], K_te.ravel()].mean()),
            "circuits_run": qk.circuits_run,
            "seconds": round(qk.seconds, 1),
            "job_ids": qk.jobs if args.backend == "ibm" else [],
        })

    print("\n" + "-" * 58)
    print(f"Exact kernel        test AUC {exact_auc:.3f}")
    if args.backend != "exact":
        print(f"{args.backend:<19} test AUC {result['backend_auc']:.3f}   "
              f"({result['circuits_run']} circuits, {result['seconds']} s)")
        print(f"Kernel error (mean |backend - exact|): {result['kernel_mean_abs_error']:.4f}")
        print(f"Average similarity: exact {result['mean_kernel_exact']:.3f}, "
              f"{args.backend} {result['mean_kernel_backend']:.3f}")
    print("-" * 58)
    print("Note: with this few test patients the AUC moves a lot between seeds; the kernel "
          "error is the cleaner measure of backend quality.")

    if not args.no_save:
        RESULTS_DIR.mkdir(exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        out = RESULTS_DIR / f"{args.backend}-{stamp}.json"
        out.write_text(json.dumps({"args": vars(args) | {"scale": scale}, "circuit": info,
                                   "result": result}, indent=2))
        print(f"Saved {out.relative_to(RESULTS_DIR.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
