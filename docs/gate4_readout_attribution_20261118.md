# PHYSQED-Q Gate 4: shot-free readout-attribution audit

**Status (18 November 2026):** exact finite-model mechanistic audit passed; results
ARE NOT current hardware or general compiler-performance claims.

The main new inference is **negative**: the Gate 3 simulated PHYSQED-Q
advantage over PyZX on a selected 3-qubit phase-cancellation witness is
driven by the HISTORICAL backend's unequal physical readout assignments.
It is **not** a demonstrated advantage of the PHYSQED gate optimiser, gate
noise, or direction-dependent CNOT calibration errors.

## Provenance and reproduction

- PR: https://github.com/tonynewton79-web/PHYSQED-Q/pull/25
- Passing original analytic run:
  https://github.com/tonynewton79-web/PHYSQED-Q/actions/runs/44287768025
- Original run code HEAD: 43787a6c7ca141290b137ea17a67ef288101f186
- Complete raw result + second-pass audit ZIP SHA-256:
  ca73cddcfb8aa594ef80212e5d1e4037469d91e89b2d882341d803b5e043d510
- Application-fixture manifest:
  edb6322110fe59e6fd1250c124cd0a3b8a9782d3a1975a1d0b5e51f01da247f6

Run from repository with pinned Gate-3 external dependencies:

    python -m pip install -r benchmarks/requirements-gate3.txt
    python -m unittest tests.test_gate4_noise_ablation tests.test_gate3_math -v
    python -m benchmarks.gate4_noise_ablation --output gate4-ablation.json
    python -m benchmarks.gate4_audit gate4-ablation.json --output gate4-audit.json

The independent second-pass standard-library audit recomputed and checked
270 density-matrix output-probability distributions (2 historical backends *
5 circuits * 3 methods * 9 conditions), normalization, exact ideal-routing
controls, output measurement mapping, physical CNOT ledgers, every TVD and
every signed contrast. Result: PASS. The independent audit is arithmetic
replay of a Qiskit/Aer data product, not a second independently coded
quantum dynamics solver.

## Prespecified post-hoc scope

Five **selected** application circuits: phase-cancel-n3,
trotter-ising-n4, ghz-n3, qaoa-path-n3, cluster-n3.
All three logical candidates undergo complete ideal-operator comparison
(PHYSQED-Q also exact receipt replay), before mapping to the SAME fake
backend, initial physical layout and Qiskit level-3 seed. Histories remain
different: the candidates can choose different physical routing and final
measurement qubits. No claim of blinded or representative workloads.

Backends: FakeManilaV2 (2024-05-27 15:27:23-03:00) and FakeLagosV2
(2024-05-27 15:51:15-03:00). Software: Qiskit 2.6.1,
PyZX 0.10.8, Aer 0.18.4, IBM Runtime 0.49.0.

Nine interventions:
ideal; historical readout-only; historical calibrated gate noise without
readout; historical calibrated gate noise + exact classical readout;
historical depolarizing-only; historical thermal-relaxation-only;
historical CX-direction-labelled depolarizing-only; CNOT-error
direction-label swap; uniform-CX 2% depolarizing-only.

Aer density matrix produces the **exact finite-model output populations**
to floating-point precision, with ZERO shot sampling (not an exact
physical model). Readout is analytically composed using the public
Aer basic_device_readout_errors(Target) matrix per **actual measured
physical qubit**; the model assumes independent single-qubit assignment
channels as in these archived device snapshots.

## Decisive phase-cancel-n3 intervention

Signed quantity = TVD(PHYSQED-Q, ideal) - TVD(PyZX, ideal);
negative favours PHYSQED-Q.

| Intervened noise | Manila signed TVD | Lagos signed TVD |
| --- | ---: | ---: |
| No noise | 0.00000 | 0.00000 |
| Historical gate noise without readout | +0.01238 | +0.01415 |
| Historical readout only | -0.07450 | -0.32760 |
| Historical gate+readout | -0.06185 | -0.31438 |
| Fixed 2% CX depolarizing, no readout | +0.02882 | +0.02882 |

The shotless combined-model result matches earlier shot-based Gate 3
results closely, while the gate-noise-only sign REVERSES.

Measured physical qubits for classical outcome bits c=0,1,2:
- PHYSQED-Q and Qiskit: [0,2,1].
- PyZX: [1,0,2].

The relevant historical per-physical-qubit single-shot average readout
errors in these snapshots are:

| Backend | Physical q1 | Physical q2 |
| --- | ---: | ---: |
| FakeManila | 0.0219 | 0.0964 |
| FakeLagos | 0.1362 | 0.4638 |

The phase-cancellation fixture has a one-bit-sensitive ideal output, so
PyZX's final measured qubit q2 contributes disproportionately. Under
readout-only noise, the signed TVD gap reproduces the q1 versus q2
readout error differential: -0.0745 (Manila), -0.3276 (Lagos).

Note: both methods have five CNOTs, but different sequences and measured
qubit allocations. Crucially the historical calibration files assign
THE SAME error probability to both physical CNOT directions for each
undirected edge (e.g. q0->q1 and q1->q0 share 0.008827712... on Manila).
Therefore, swapping the directional CX calibration labels changes
nothing: **a direction-specific CNOT error-rate mechanism is ruled out
within these historical snapshots**. Differences in gate-only TVD may
depend on native circuit ordering, decomposition, and states; this audit
does not prove a unique gate-noise causal mechanism.

For all FIVE fixtures, both backends:
- PHYSQED-Q versus Qiskit: exactly tied across all 9 modeled conditions.
- PHYSQED-Q versus PyZX, full readout+gate model: 3 numerically better,
  1 approximately tied and 1 worse at the 2e-7 numerical threshold
  for each backend. This is a purpose-selected small POST-HOC set,
  not a statistically general success rate or external ranking.

## Exact rational readout-allocation identity (elementary, not novelty)

The **ideal 3-qubit phase-cancellation circuit** generates

    p(x2,x1,x0) = (1/4) * 1[x2=0].

Thus low bits x0 and x1 are exactly uniform, and x2 is exactly zero.
For independent **symmetric** binary-readout channels, the uniform
low-bit marginals remain invariant. If the physical qubit measured for
classical bit x2 has bit-flip probability e, the observed distribution
has probability (1-e)/4 on each x2=0 string and e/4 on each x2=1
string. Therefore

    TVD(observed_readout_only, p) = e       EXACTLY.

The other two qubits' symmetric readout error probabilities cancel from
this particular TVD. This is a standard stochastic-channel identity.

On the archived snapshots, PHYSQED-Q measures x2 on physical q1,
PyZX measures x2 on physical q2. Hence the readout-only signed contrast
is **exactly** e(q1)-e(q2), requiring no quantum simulator:

    FakeManila:  219/10000 - 964/10000   = -745/10000  = -0.0745
    FakeLagos: 1362/10000 - 4638/10000  = -3276/10000 = -0.3276

The project now has an independently replayed test using
Python fractions.Fraction across 80 rational readout-error combinations,
plus both exact archived contrasts. For asymmetric, correlated or
context-dependent measurement channels, this simple identity does NOT
automatically apply.

## Why this matters scientifically

It is a real methodological correction: a compiler may look better in
an end-to-end historical noisy simulation *solely because its physical
measurement allocation encounters a better calibrated readout qubit*.
A comparison of output TVD against an ideal (unmitigated) reference is
sensitive to differences in the classical measurement channel.

This is fully consistent with physical expectations and existing
noisy-compiler prior art; NOT a new theorem of quantum mechanics or
a real superconducting-device performance demonstration.

## What would clear the next physical gate?

Independently provided 2-4-qubit quantum-processor circuits and **live
hardware data**, with dated QPU Target/error/measurement calibration,
predeclared objective, randomized/interleaved allocation and execution,
matched physical measurement qubits or explicit allocation optimization
for ALL candidate compilers, calibrated readout mitigation with
uncertainty propagation, and repeated independent shot batches.

No PHYSQED-Q superconducting fidelity superiority, general T-count
advantage, or improved experimental hardware performance is established.
