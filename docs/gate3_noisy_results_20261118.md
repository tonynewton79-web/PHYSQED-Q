# PHYSQED-Q Research Gate 3 — noisy applications and two-backend stress test

**18 November 2026. Research status: bounded positive SIMULATED result,
no live-device or general compiler superiority claim.**

## Provenance: unmodified first run

- Exact source head: 279e007e8e2cddec0e7bcac6dc1fa52ea9f5dad5
- GitHub Actions: https://github.com/tonynewton79-web/PHYSQED-Q/actions/runs/44218561337
- Original raw artifact SHA-256:
  429796ea121471aa6389f263a9be3c81ac672125f7e392d041a2c1ff2d9dbec7
- Locked application manifest SHA-256:
  edb6322110fe59e6fd1250c124cd0a3b8a9782d3a1975a1d0b5e51f01da247f6

The 15 synthetic application-style circuits are GHZ, graph-cluster,
path-MaxCut QAOA at Clifford+T angles, two-step Ising Trotter,
and phase-cancellation; 2, 3 and 4 logical qubits per family.
**Not independent laboratory workloads**. Every PHYSQED exact receipt
passed, and all baseline operators were checked up to global phase
before the noisy model was used.

Python versions: Qiskit 2.6.1, PyZX 0.10.8, Qiskit Aer 0.18.4,
IBM Runtime 0.49.0. Same Qiskit level-3 native compiler, seed 2026,
physical initial layout [0,1,...] and historical FakeManilaV2 backend.
Backend calibration timestamp 2024-05-27 15:27:23-03:00.
Each candidate: 4096 simulated shots with seed 20261118 and
4096 with seed 20261119, aggregated to 8192.

Primary quantity is TVD (total variation distance) of the observed
bitstring distribution from the corresponding noiseless ideal target.
Less TVD is better. A separate ideal native-circuit simulation checked
mapping and measurement bookkeeping.

A *familywise* 5% simultaneous Monte Carlo TVD radius was computed from
the 2^m-form multinomial/Bretagnolle-Huber-Carol upper bound over
90 modeled distributions (15 circuits * 3 compilers * noisy/ideal).
This addresses simulator shot variation, NOT calibration uncertainty,
real-device drift, or underlying systematic model error.

### First run

| Comparison | PHYSQED separated better | Inconclusive | PHYSQED separated worse |
| --- | ---: | ---: | ---: |
| PHYSQED versus Qiskit | 0 | 15 | 0 |
| PHYSQED versus PyZX | 1 | 14 | 0 |

The successful separation was phase-cancel-n3:
PHYSQED TVD 0.0380859375, PyZX TVD 0.0997314453,
difference -0.0616455078, simultaneous two-candidate TVD
uncertainty margin 0.0564249004. Both native circuits used FIVE CNOTs.

All 15 PHYSQED and Qiskit native gate-count histograms and
pseudo-random shot counts were identical under the fixed seeds.
Thus this study showed **no advantage over Qiskit**.

## Post-hoc robustness (not a second blinded corpus)

- Robustness study head at first completion:
  d0aed9de5994b9689bb8efd82f3c76a9e8e6a83a
- GitHub Actions:
  https://github.com/tonynewton79-web/PHYSQED-Q/actions/runs/44219330836
- Full ZIP SHA-256:
  9d04e1795399043de17877ab1e7dd28091f717b9ecfc6bdc7155fbfeb7777bc5
- Same 15 circuit definitions; fresh seeds 20261120 and 20261121,
  4096 shots each; two distinct historical fake-backend snapshots.
- A stronger 5% simultaneous Monte Carlo margin was computed over
  180 simulated distributions (2 backends * 15 circuits *
  3 methods * noisy/ideal).

| Backend | PHYSQED better than PyZX beyond sampling threshold | Inconclusive |
| --- | ---: | ---: |
| FakeManilaV2 | 1 | 14 |
| FakeLagosV2 | 2 | 13 |

Against Qiskit, 15/15 comparisons per backend were inconclusive,
with no demonstrated benefit. Both historical backend dates are
2024-05-27 (Manila 15:27:23 -03:00, Lagos 15:51:15 -03:00).

For the same phase-cancel-n3 circuit:

| Backend | PHYSQED TVD | PyZX TVD | Signed PHYS minus PyZX | Simultaneous separation margin |
| --- | ---: | ---: | ---: | ---: |
| FakeManila | 0.0363769531 | 0.0969238281 | -0.0605468750 | 0.0579050496 |
| FakeLagos | 0.1501464844 | 0.4643554688 | -0.3142089844 | 0.0579050496 |

**Additional stress:** on FakeLagos, trotter-ising-n4 also
crossed the margin: PHYSQED TVD about 0.39784, PyZX 0.46837,
difference -0.07053 versus a margin about 0.06861.

In phase-cancel-n3, PHYSQED and PyZX both have five physical CNOT
operations, yet the physical CNOT orientation sequence differs:
PHYSQED: (0,1),(1,2),(2,1),(1,2),(0,1).
PyZX: (1,0),(0,1),(1,0),(2,1),(1,0).
Thus aggregate CNOT count does NOT determine performance under an
edge- and direction-dependent calibration/noise model. Differences
in direction/order are observed, not proven to be the sole causal
source of the simulated outcome.

## Exact logical versus noisy physical operation

Equality of ideal unitaries does not imply equality of noisy channels.
For a toy bit-flip error p after each X operation, XX = I ideally,
yet the two-X device has final bit-error probability 2p(1-p),
while the empty identity does not incur gate-associated bit flips.

This is elementary physics, not a new theorem, but is a necessary
verification boundary for the project.

## Audit and limitations

Both original and robustness CI jobs completed successfully. A
separate standard-library numerical second pass independently
recomputed all raw-shot TVD values, union-bound thresholds, per-case
summary counts, 15/15 and 30/30 circuit coverage, and ZIP digests.
It did **not** independently reimplement Qiskit, PyZX, Aer or the
underlying device noise model.

The benchmarks are deliberately small, synthetic, and chosen by the
PHYSQED-Q author. Hardware simulations use 2024 archived snapshots,
not current QPU measurements; modeled errors omit calibration drift,
pulse-level leakage, coherent cross-talk and full queue-dependent idle
effects. The quoted Monte Carlo bounds are not error bars on an actual
superconducting system. No external T-count or T-depth advantage and
no real-device physical-fidelity superiority has been established.

**Decisive next physical experiment:** ask an independent superconducting
laboratory for a genuine 2-4-qubit unitary workload and a current dated
backend Target/calibration; compare fixed native compilation and
control/target orientation under interleaved on-device sampling,
including readout mitigation policy, randomized runs and error bars.
Prespecify the device-level success metric and required effect margin.
A single archived fake backend can never certify actual hardware gain.

Research status: limited simulated-noise positive result versus PyZX
in 1/15 initially, and posthoc two-backend confirmation of the same
case; parity with Qiskit on all tested cases; real-hardware claim open.
