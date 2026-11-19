"""
Quantum kernel matrices, computed on any backend.

    k = QuantumKernel("noisy", shots=2000)
    K_train = k.matrix(X_train)            # symmetric, n(n-1)/2 circuits
    K_test  = k.matrix(X_test, X_train)    # n_test * n_train circuits

X must already be rotation angles (see data.AngleScaler).

Error mitigation (mitigate=True)
--------------------------------
On noisy hardware the measured probability shrinks towards random guessing.
Modelling the noise as global depolarisation with survival factor f,

    p_measured = f * k + (1 - f) / 2^n.

Each patient is also run against itself, where the true kernel is exactly 1,
which gives f for that patient. The kernel is then corrected as

    k_ij = (p_ij - 1/2^n) / ((1 - 1/2^n) * sqrt(f_i * f_j))

(the depolarising-noise correction used in quantum-kernel hardware studies).
It costs one extra circuit per patient.
"""

import time

import numpy as np

from . import backends, circuits


class QuantumKernel:
    def __init__(self, kind="exact", shots=2000, reps=circuits.REPS,
                 entanglement=circuits.ENTANGLEMENT, num_qubits=circuits.NUM_FEATURES,
                 fake=backends.DEFAULT_FAKE, ibm_backend=None, optimization_level=3, seed=None, mitigate=False):
        self.kind = kind
        self.mitigate = mitigate and kind != "exact"
        self._self_overlap = {}  # cache: patient row bytes -> measured P(0...0) against itself
        self.shots = int(shots)
        self.reps = reps
        self.entanglement = entanglement
        self.num_qubits = num_qubits
        self.seed = seed
        self.backend = backends.get_backend(kind, fake=fake, ibm_backend=ibm_backend)
        self.circuit = circuits.kernel_circuit(num_qubits, reps, entanglement)
        self.isa_circuit = None
        self.jobs = []          # job ids (useful for hardware runs)
        self.circuits_run = 0
        self.seconds = 0.0
        if self.backend is not None:
            from qiskit.transpiler import generate_preset_pass_manager

            pm = generate_preset_pass_manager(optimization_level=optimization_level,
                                              backend=self.backend, seed_transpiler=seed)
            # "ISA" circuit: rewritten into the device's native gates and qubit connectivity.
            self.isa_circuit = pm.run(self.circuit)
            self.sampler = backends.get_sampler(kind, self.backend)

    # ---------- reporting ----------
    def report(self) -> dict:
        out = {
            "backend": backends.describe(self.kind, self.backend),
            "shots": None if self.backend is None else self.shots,
            "logical_circuit": circuits.circuit_stats(self.circuit.decompose(reps=2)),
        }
        if self.isa_circuit is not None:
            out["device_circuit"] = circuits.circuit_stats(self.isa_circuit)
            layout = self.isa_circuit.layout
            if layout is not None:
                out["physical_qubits"] = [int(q) for q in layout.final_index_layout()]
        return out

    def circuits_needed(self, n_a: int, n_b: int | None = None) -> int:
        """Circuits for a kernel matrix; with mitigation, plus one self-overlap per new patient."""
        pairs = n_a * (n_a - 1) // 2 if n_b is None else n_a * n_b
        extra = n_a if self.mitigate else 0  # rows of XA (training rows are already cached for XB)
        return pairs + extra

    # ---------- kernel ----------
    def matrix(self, XA, XB=None) -> np.ndarray:
        XA = np.atleast_2d(np.asarray(XA, float))
        symmetric = XB is None
        XB = XA if symmetric else np.atleast_2d(np.asarray(XB, float))
        if self.backend is None:
            sa = circuits.statevectors(XA, self.reps, self.entanglement)
            sb = sa if symmetric else circuits.statevectors(XB, self.reps, self.entanglement)
            return np.abs(sa.conj() @ sb.T) ** 2

        if symmetric:
            ii, jj = np.triu_indices(len(XA), k=1)   # k(x, x) = 1, and k is symmetric
        else:
            ii, jj = (g.ravel() for g in np.meshgrid(np.arange(len(XA)), np.arange(len(XB)),
                                                       indexing="ij"))
        values = self._estimate(XA[ii], XB[jj])
        K = np.ones((len(XA), len(XA))) if symmetric else np.empty((len(XA), len(XB)))
        if self.mitigate:
            fa = self._survival(XA)
            fb = fa if symmetric else self._survival(XB)
            floor = 1.0 / 2 ** self.num_qubits
            values = (values - floor) / ((1 - floor) * np.sqrt(fa[ii] * fb[jj]))
            values = np.clip(values, 0.0, 1.0)
        K[ii, jj] = values
        if symmetric:
            K[jj, ii] = values
        return K

    def _survival(self, X) -> np.ndarray:
        """Depolarising survival factor f for each patient, from running k(x, x)."""
        keys = [x.tobytes() for x in X]
        todo = [i for i, k in enumerate(keys) if k not in self._self_overlap]
        if todo:
            for i, p in zip(todo, self._estimate(X[todo], X[todo])):
                self._self_overlap[keys[i]] = p
        floor = 1.0 / 2 ** self.num_qubits
        p = np.array([self._self_overlap[k] for k in keys])
        return np.clip((p - floor) / (1 - floor), 1e-3, 1.0)

    def _estimate(self, xs, ys, batch=1000) -> np.ndarray:
        """P(all zeros) for each pair, from measured shots."""
        out = []
        start = time.perf_counter()
        for s in range(0, len(xs), batch):
            params = circuits.bind_pairs(self.isa_circuit, xs[s:s + batch], ys[s:s + batch])
            job = self.sampler.run([(self.isa_circuit, params, self.shots)])
            try:
                self.jobs.append(job.job_id())
            except Exception:
                pass
            bits = job.result()[0].data.meas          # BitArray, shape (pairs,), `shots` each
            raw = bits.array                          # (pairs, shots, bytes) packed bits
            out.append(np.all(raw == 0, axis=-1).mean(axis=-1))
        self.circuits_run += len(xs)
        self.seconds += time.perf_counter() - start
        return np.concatenate(out)
