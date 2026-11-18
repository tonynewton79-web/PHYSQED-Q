# PHYSQED-Q Gate 6 — executable common-output physical routing

**Research date:** 18 November 2026.
**Status:** post-hoc, historical-model, native-executable circuit analysis. The
selected circuits and all physical simulation output have been independently
checked numerically. **No live superconducting experiments, general T-count
superiority, or experimental hardware performance advantage.**

## Provenance

- Open draft PR: https://github.com/tonynewton79-web/PHYSQED-Q/pull/27
- First fully passing hosted CI:
  https://github.com/tonynewton79-web/PHYSQED-Q/actions/runs/44291165575
- Code commit: bdb0205182bde0c0a151c1da0cc4cf51cf658577
- Hosted ZIP artifact ID: 14422355354
- Hosted ZIP SHA-256:
  8f06179d0f9c8280ea66a17c6ed2465758e5fc8503c2d10e4c59d69930fa04a4
- Fixed application-suite manifest:
  edb6322110fe59e6fd1250c124cd0a3b8a9782d3a1975a1d0b5e51f01da247f6

## Methods and why Gate 6 resolves Gate 5's main limitation

Gate 5 counterfactually applied a common classical measurement channel
while leaving different physical circuit layouts unchanged. This was not
an executable physical-routing intervention.

Gate 6 instead compiles each PHYSQED-Q, Qiskit 2.6.1 and PyZX 0.10.8
candidate to the same historical fake IBM backend, routes any mismatched
output quantum states to an explicitly fixed physical output allocation,
then actually appends a native SWAP network and native measurements.
The SWAP network is a shortest-edge-token-route BFS on the finite backend
coupling graph, and is decomposed to the backend native Target at
optimization_level=0, thereby retaining the full native routing overhead.

Noiseless full-output probabilities of every mapped native circuit are
independently verified to match its ideal logical unitary's computational
basis measurement distribution (tolerance 2e-7).
Every physical output measurement is checked against the required
classical-bit -> physical-qubit mapping. Noise outcomes use Aer
density-matrix gate noise from dated backend properties plus the
corresponding physical-qubit readout assignment probabilities.
The gate ledger includes native operations, required output qubits,
SWAP trace, two-qubit counts and ASAP durations *excluding readout*.
No Monte Carlo shot-sampling uncertainty is present; this does not
include real calibration uncertainty, temporal drift, coherent
interference with environment, or all correlated noise.

The scope is small and specifically post-hoc: five application-style
2-4-qubit synthetic circuits, two historical backend models
(FakeManilaV2 and FakeLagosV2, last calibrated 27 May 2024), and
two predeclared common output locations for each n:
identity (0,1,..,n-1) and reverse (n-1,..,1,0).
This gives 5*2*2*3 = 60 native candidate circuits.

## Decisive phase-cancellation witness

Numbers are signed TVD(PHYSQED-Q)-TVD(PyZX), where negative is better
for PHYSQED-Q.

| Historical backend | Common physical outputs ascending | Common physical outputs reversed |
| --- | ---: | ---: |
| FakeManilaV2 | +0.01725936 | +0.00411870 |
| FakeLagosV2 | +0.00207001 | -0.00055144 |

The large old simulated PHYSQED-Q advantage of 0.0618 TVD on Manila
and 0.3144 on Lagos under *unequal final readout assignments* has
disappeared. With common output allocations, both pipelines have
identical native 2Q counts on this witness:
8 native two-qubit gates in the ascending configuration, 11 in reverse.

PHYSQED and Qiskit remain identical in output probability and physical
native 2Q cost on every tested backend*placement*case combination.

The small Lagos negative gap of 0.00055 in the reverse case is
specific to this historical model; it is not a significant experimental
fidelity result or a general compiler advantage.

## A separate Trotter-specific native compilation difference

On the four-qubit Ising-Trotter fixture, the PHYSQED-Q and Qiskit
frontend native pipelines require fewer two-qubit operations than the
PyZX full_optimize->Qiskit native pipeline, with routing included.

| Backend | Common outputs | PHYSQED and Qiskit native 2Q | PyZX native 2Q | PHYS minus PyZX noisy TVD |
| --- | --- | ---: | ---: | ---: |
| FakeManilaV2 | ascending | 12 | 26 | -0.06567349 |
| FakeManilaV2 | reversed | 30 | 38 | -0.04861836 |
| FakeLagosV2 | ascending | 18 | 40 | -0.02536454 |
| FakeLagosV2 | reversed | 24 | 34 | -0.02346805 |

These are physically matched historical-model *compiled-circuit*
comparisons, not a general PyZX comparison or a measured QPU
result. The win is **not unique to PHYSQED-Q** because Qiskit matches
all PHYSQED-Q outcomes on this workload as well.

This circuit is both selected post hoc and an unusually sensitive
small-instance routing example; the difference could disappear under
other settings, stronger PyZX+hardware-aware optimisation, or different
device targets. Do not call the difference a universal T-count
or native-performance advantage.

## Signed model output counts on all five selected circuits

"Better" means strictly lower simulator TVD at a 1e-7 numerical margin,
not a confidence-bound inference across a representative workload.

| Historical backend | Common outputs | PHYS lower vs PyZX | Tie | PHYS higher vs PyZX |
| --- | --- | ---: | ---: | ---: |
| FakeManilaV2 | ascending | 2 | 1 | 2 |
| FakeManilaV2 | reversed | 2 | 1 | 2 |
| FakeLagosV2 | ascending | 2 | 1 | 2 |
| FakeLagosV2 | reversed | 3 | 1 | 1 |

Against Qiskit all twenty paired cases tie.

## Exact/certification status

Original GitHub Actions gate6 job passed: 60/60 native-candidate ideal
probability controls. An independent standard-library Python audit
recomputed every classical readout pushforward, normalized noisy
probability distribution, TVD, signed comparison and aggregate result;
replayed physical SWAP movements and checked that all actual native
measurements end on the specified physical output qubits. The audit
found all 60 records consistent, with no invalid two-qubit couplings.

This is an independent *report and routing* audit, not an independent
quantum density-matrix calculation and not a quantum-processor
measurement. Python full-operator receipts and ideal unitary checks
are separate preceding logical guarantees.

## Next decisive gate

Remove the remaining 2024-backend and case-selection dependence:
predeclare independently supplied workloads, evaluate held-out
benchmark programs with a fair PyZX phase-polynomial and circuit-aware
native optimisation pipeline, use multiple Qiskit seeds, calibrated
same-physical-output constraints, and repeat on *current* backend
Targets. Validate performance under actual randomized/interleaved
quantum-computer measurements, including readout mitigation,
physical-wire calibration uncertainty and inferential error bars.

No claim of established general T-count, T-depth, hardware duration,
or true physical-fidelity superiority is warranted.
