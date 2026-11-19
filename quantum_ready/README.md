# quantum_ready: RiskPredict's quantum kernel, ready for real hardware

The web app (`final_app/`) runs its quantum kernel SVM with **exact statevector
simulation**: fast, deterministic, no noise. That is standard practice for
research and training, but it is not how a quantum computer works.

This folder runs the **same 10-qubit circuit the way a quantum computer would**:
as measured shots, compiled into a real device's native gates and qubit layout.
The same code can target four backends:

| Backend | What it is | Needs |
|---|---|---|
| `exact` | Statevector maths (what the web app does) | nothing |
| `ideal` | Qiskit Aer simulator: real shot sampling, perfect qubits | nothing |
| `noisy` | Aer with the noise model, gates and connectivity of IBM's 133-qubit **Torino** processor | nothing |
| `ibm` | A real IBM Quantum computer via Qiskit Runtime | an IBM Quantum API key |

Moving from `noisy` to `ibm` changes only which backend object is passed in.
The circuit, compilation, sampler and error mitigation code are the same.

## Setup

From the repository root, in the project's virtual environment:

```powershell
pip install -r quantum_ready/requirements.txt
cd quantum_ready
python check_setup.py
```

`check_setup.py` checks the libraries, runs a Bell-state test on the simulator,
loads the real-device noise model, builds the project circuit and looks for IBM
credentials. Its summary says what is ready.

## Run it

```powershell
python run_experiment.py --backend ideal
python run_experiment.py --backend noisy --train 20 --test 20 --shots 1000 --entanglement linear
python run_experiment.py --backend ibm --dry-run
```

Each run:

1. picks a small stratified set of synthetic patients from
   `final_app/data/synthetic_patients.csv` (read only),
2. scales their 10 features to rotation angles,
3. measures the kernel (patient similarity) with fidelity circuits,
4. trains an SVM on that kernel and scores the test patients (AUC),
5. does the same with the exact kernel and reports how far the backend is off.

Results are saved to `results/`. `--dry-run` only compiles the circuit for the
device and prints the depth, two-qubit gate count, physical qubits and number of
shots a run would need, without executing anything.

## How a kernel value is measured on hardware

A quantum computer can't hand over its state vector, so the similarity of
patients *x* and *y* is measured with the compute-uncompute test:

```
|0…0⟩ ── U(x) ── U(y)† ── measure all 10 qubits
```

The share of shots where every qubit reads 0 is exactly
`|⟨ψ(y)|ψ(x)⟩|²`, the kernel value. A training set of *n* patients needs
*n(n−1)/2* circuits, and *m* test patients need *m·n* more.

## Error mitigation

On noisy hardware, every measured similarity shrinks towards random guessing.
With mitigation on (the default for `noisy` and `ibm`), each patient is also run
against itself. That answer should be exactly 1, so the gap shows how much
signal the noise destroyed, and the kernel is rescaled using a global
depolarising-noise model. It costs one extra circuit per patient. Turn it off
with `--no-mitigation`. Real hardware runs also enable dynamical decoupling and
gate twirling in Qiskit Runtime.

## Results so far (simulators)

Run on 20 Nov 2026 with the 10-feature model (the app's 4 main genes + "other gene
risk" + 5 more); the raw output is in `results/`. All runs use random seed 0.

| Backend | Circuit | Two-qubit gates on chip | Patients (train / test) | Kernel error vs exact | Average similarity (exact → backend) | Test AUC (exact → backend) |
|---|---|---|---|---|---|---|
| ideal | full entanglement (as in the app) | 358 | 40 / 40 | **0.007** | 0.461 → 0.461 | 0.375 → 0.363 |
| noisy, no mitigation | linear | 70 | 20 / 20 | 0.342 | 0.872 → 0.530 | 0.484 → 0.344 |
| noisy, with mitigation | linear | 70 | 20 / 20 | **0.022** | 0.872 → 0.868 | 0.484 → 0.484 |
| noisy, with mitigation | full entanglement | 828 | 20 / 20 | 0.165 | 0.483 → 0.534 | 0.609 → 0.641 |

**Read the kernel error, not the AUC.** Seed 0 happens to be an unlucky patient
sample: with only 4–8 positive test patients the AUC swings a lot. Across 10
random samples the *exact* kernel averages AUC 0.66 ± 0.12 (40 / 40 patients,
full entanglement) and 0.70 ± 0.17 (20 / 20, linear), and seed 0 is the worst
draw in both. The useful comparison is that each backend matches the exact
answer (the same AUC on the same patients), and the kernel error measures that
directly.

What this shows:

- **The circuit measurement is correct.** The ideal shot-based simulator matches
  the exact kernel to within shot noise (0.007).
- **Noise matters, and mitigation handles much of it.** With the real-device
  noise model, raw similarities drop from 0.87 to 0.53 on average. Mitigation
  brings them back to 0.87, the kernel error falls from 0.34 to 0.02, and the
  model gives the same AUC as the exact kernel.
- **Circuit depth is the limit.** The web app's full-entanglement circuit becomes
  ~830 two-qubit gates once routed onto the chip. Even with mitigation its error
  stays at 0.17. Linear entanglement needs only ~70, which today's hardware can
  run far more faithfully. That's why `--entanglement linear` is recommended for
  hardware runs.

## Running on real IBM hardware

IBM's free **Open Plan** gives up to 10 minutes of real quantum processor time
per month, which is enough for a small run.

1. Create an account at <https://quantum.cloud.ibm.com> and copy your API key.
2. `python ibm_login.py` and paste the key (it is saved by Qiskit in your user
   folder, `~/.qiskit/`, never in this project).
3. `python check_setup.py --online` lists the devices you can use.
4. Check the cost first, then run a small job:

```powershell
python run_experiment.py --backend ibm --train 20 --test 10 --shots 1000 --entanglement linear --dry-run
python run_experiment.py --backend ibm --train 20 --test 10 --shots 1000 --entanglement linear
```

Jobs wait in IBM's queue (minutes to hours). The job IDs are saved in the result
file, and you can look them up on the IBM Quantum dashboard.

## Files

| File | Purpose |
|---|---|
| `qready/circuits.py` | ZZ feature map and the fidelity (kernel) circuit |
| `qready/backends.py` | exact / ideal / noisy / ibm backends and samplers |
| `qready/kernel.py` | kernel matrices from measured shots, with error mitigation |
| `qready/data.py` | reads the synthetic cohort, stratified sampling, angle scaling |
| `qready/_aer_fix.py` | works around a qiskit-aer import bug when the venv sits inside a git repo |
| `check_setup.py` | environment and readiness check |
| `run_experiment.py` | the experiment runner |
| `ibm_login.py` | saves an IBM Quantum API key locally |
| `tests/` | `python -m pytest -q tests` (circuit correctness, match with the web app, mitigation) |

## Honest limits

- The data is the project's synthetic cohort, not real patients.
- Hardware-sized experiments use tens of patients, not the web app's 1,500,
  because every pair of patients is a separate circuit.
- The angle scale is 0.02 here (the app's 0.1 was tuned for 1,500 training
  patients; with tens of patients a smoother kernel works better).
- No quantum advantage is claimed: on this problem the classical random forest
  is still the strongest model (see the web app's Models page).
