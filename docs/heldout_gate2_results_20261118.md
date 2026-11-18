# PHYSQED-Q Gate 2 — held-out benchmark results, 18 November 2026

**Research finding: NO general T-count advantage or superconducting-hardware
improvement has been demonstrated.**

Reproducible first-result code commit:
6d624e91a3336f1a8d8c3ca29deaa08e25590564

First verified CI and downloadable original report:
https://github.com/tonynewton79-web/PHYSQED-Q/actions/runs/44216516198

Held-out manifest SHA-256:
2aae17d5bc05a540507e094f8e80f7e261aa7371dd6e8594cc2556f5b6c826a8

Artifact ZIP SHA-256:
4d8e7815c5c2fc89f2e6205303f7717a37cdd3fdc6f4393584a20ee67c6f2eaf

## Held-out logical T-count (40 synthetic circuits, 2-4 qubits)

| Baseline | PHYSQED fewer T | Equal | PHYSQED more T |
| --- | ---: | ---: | ---: |
| Qiskit 2.6.1, level 3 | 0 | 40 | 0 |
| PyZX 0.10.8, full_optimize | 0 | 39 | 1 |

All external outputs passed an independent unitary comparison up to
global phase (absolute tolerance 1e-9). PHYSQED outputs additionally
passed exact Python receipt replay. No baseline output failed or was
excluded from the paired results.

The only logical T-count difference occurred at heldout-mixed-03:
PHYSQED-Q = 4, Qiskit = 4, PyZX = 2. This is **negative** evidence for
a broad PHYSQED-Q optimisation-supremacy claim.

## Historical native instruction properties (20 fixed matched cases)

Backend: FakeManilaV2 (five qubits). IBM runtime version 0.49.0.
Historical last-calibrated timestamp: 2024-05-27 15:27:23-03:00.
Same initial qubit layout, backend, routing and fixed Qiskit level-3
transpilation seed 2026 for all logical frontend candidates.

| Comparison | PHYSQED lower | Equal | PHYSQED higher |
| --- | ---: | ---: | ---: |
| Native 2-qubit gates versus Qiskit | 0 | 20 | 0 |
| ASAP duration proxy versus Qiskit | 0 | 20 | 0 |
| Native 2-qubit gates versus PyZX | 5 | 14 | 1 |
| ASAP duration proxy versus PyZX | 5 | 13 | 2 |

A naive independent gate-survival proxy versus Qiskit tied 20/20.
Versus PyZX it was higher on 7, tied on 12, lower on 1 for PHYSQED.

**Not live hardware results.** ASAP gate duration and gate-error-product
estimates are model proxies and ignore readout, idle decoherence,
correlated noise, leakage, pulse dynamics and crosstalk.

The logical T-count winner in heldout-mixed-03 (PyZX, T=2)
actually needed more native 2Q operations under this snapshot
(PyZX six vs PHYSQED three) and had a larger duration proxy
(about 2802 ns vs about 1323 ns). Logical T cost and native
physical costs are different quantities.

## Methodology and independent audit

The held-out fixed-seed corpus has 40 circuits: 10 each of four designed
families (control-phase, target-negative, mixed and phase-heavy),
seed 2026111802. A separate development split uses seed 2026111801
and 12 cases. This tiny, synthetic, purpose-designed corpus is not a
representative sample of general quantum workloads.

The actual CI passed Qiskit/PyZX comparisons plus Python regression and
Lean checks. A post-download independent Python second-pass audit
recomputed the recorded 40-case logical comparisons and 20-case native
coverage, checked every report-equivalence and exact-replay flag, and
verified no recorded case errors. This second-pass arithmetic audit
is **not** a second independently implemented quantum compiler.

A general T-count or T-depth advantage, live hardware performance
advantage, publication priority claim or experimental fidelity improvement
is expressly not established.

Next decisive objective: independent real-application circuits from a
superconducting-processor laboratory, a current device Target and dated
calibration, native-gate and pulse-aware cost accounting, repeated matched
Qiskit/PyZX/TKET tests and measured device outcomes with uncertainties.
