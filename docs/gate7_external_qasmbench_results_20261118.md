# PHYSQED-Q Gate 7: independently authored PNNL QASMBench benchmark

**Result status:** externally sourced, reproducible 2–4-qubit logical and
historical noisy-native benchmark, with a complete admission/refusal ledger.
No real QPU experiment or general compiler performance advantage.

## Frozen external provenance

The upstream benchmark is *PNNL QASMBench*:
https://github.com/pnnl/QASMBench (Ang Li et al., ACM TQC, DOI
10.1145/3550488). Its QASM source files are NOT republished here;
their upstream license metadata is NOASSERTION, so audit upstream
permissions before distributing the originals.

Before test execution, 19 named source files from QASMBench/small were
pinned to commit **357b942396d5c2b7cbc1c229c585a6ef5ccaebac**
and their exact Git blob SHA-1 values recorded in
benchmarks/gate7_qasmbench.py. The hosted workflow checks every
downloaded file's original Git content hash. All 19 QASM source SHA-256
values and exact refusal reasons are included in the raw machine JSON.
No custom approximation silently substitutes unsupported source gates.

## Admission coverage: 10 / 19

Strict PHYSQED-Q input: 2–4 qubits, <=200 supported logical gates,
all-qubit final identity-index measurements, no classical feedback,
and alphabet H/X/Z/S/SDG/T/TDG/CNOT/CZ/SWAP.

**Accepted:** adder_n4, cat_state_n4, deutsch_n2, fredkin_n3,
grover_n2, hs4_n4, iswap_n2, qrng_n4, teleportation_n3, toffoli_n3.

**Refused:** basis_change_n3, basis_trotter_n4, bell_n4, dnn_n2,
inverseqft_n4, linearsolver_n3, qaoa_n3, qft_n4, quantumwalks_n2.

All refusals are recorded, including unsupported general rotations,
classically controlled/mid-measurement operations and one QASM parsing
incompatibility. This is limited **coverage**, not incorrect acceptance.

## Fixed comparison

- Logical: actual PHYSQED-Q exact replay receipts, Qiskit 2.6.1
  optimization level 3, PyZX 0.10.8 full_optimize. All passed the
  same independent operator-equivalence test. Exact T counts are
  identical across the three compilers for all 10 accepted circuits:
  adder 8; cat 0; Deutsch 0; Fredkin 7; Grover 0; HS4 0;
  iSWAP 0; QRNG 0; teleportation 1; Toffoli 7.
- Physical native comparison: seeds 2026, 2031, 2081;
  ascending and reversed **executable** measured-output placements;
  archived FakeManilaV2 and FakeLagosV2 (2024 calibrations).
  Explicit native neighbour SWAPs are included in physical circuits,
  gate counts, duration proxies and Aer density-matrix simulations.
- Candidate circuits: 10 accepted × 2 historical backends ×
  3 native seeds × 2 measured-output maps × 3 compilers = **360**.
  Each of the 360 passed ideal native output checks and the separately
  implemented numerical ledger auditor.

### PHYSQED-Q versus Qiskit

All **120** corresponding native paired comparisons have equal
two-qubit count, gate-noise TVD and full noisy TVD. There is **no
demonstrated distinctive PHYSQED-Q advantage** over Qiskit in this test.

### PHYSQED-Q versus PyZX: full noisy TVD

Counts of lower / equal / higher TVD (lower is better):

| Historical backend | Output map | Lower | Equal | Higher |
| --- | --- | ---: | ---: | ---: |
| FakeManilaV2 | ascending | 12 | 6 | 12 |
| FakeManilaV2 | reverse | 9 | 6 | 15 |
| FakeLagosV2 | ascending | 11 | 6 | 13 |
| FakeLagosV2 | reverse | 11 | 6 | 13 |

Each row is 10 external circuits × 3 compilation seeds = 30
**correlated** comparisons, not 30 independent applications.
The native two-qubit gate-count comparison is sometimes favourable
to PHYSQED-Q but is not a general fidelity superiority.

On the ascending physical output layout of FakeManilaV2, for example:
- 4-qubit adder: PHYSQED and Qiskit 22 native 2Q gates,
  PyZX 37, with modelled full TVD roughly 0.300 versus 0.368;
- 3-qubit Fredkin: PHYSQED and Qiskit native 2Q counts
  [12, 12, 16] across seeds, PyZX [19,19,19], but PHYSQED's
  modelled full TVD was HIGHER than PyZX's on all three seeds.
Thus gate count alone does not determine predicted output error.

## Verification

Original hosted run: https://github.com/tonynewton79-web/PHYSQED-Q/actions/runs/44295117039
and draft PR: https://github.com/tonynewton79-web/PHYSQED-Q/pull/28

Original hosted ZIP artifact #14423855260:
SHA-256 **859e365719ec325afaab5ef1890b962293d070f90b9a4263bdadbb645dd41d32**.
The independently coded report auditor recomputed all 19 admission
decisions/counts, all 360 native-circuit physical measurement maps,
two-qubit operation counts, full recorded TVDs, signed pairwise
differences and 24 summary aggregates. Audit result: PASS.
It did not independently reimplement Aer/Qiskit's quantum dynamics.

This research compares HISTORICAL MODEL SIMULATIONS using May 2024
calibration snapshots, not current IBM Quantum hardware, live QPU shots,
actual 2026 calibrations, or a statistically representative population.
A stricter held-out blind external evaluator or independent hardware
measurement remains outstanding.

**Next objective:** expand exactly verified admissibility to more of the
nine refused QASMBench circuits (with a sound treatment of non-Clifford+T
angles and mid-circuit classical control), OR establish a predeclared,
wider benchmark against a hardware-aware PyZX+Qiskit compiler pipeline,
with all differences resolved at identical actual native placements.
No unsupported gates should be approximated silently.
