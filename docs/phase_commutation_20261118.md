# Phase-commuting T cancellation: exact restricted upgrade (18 November 2026)

**Status:** opt-in research branch. This is an exact logical optimisation result, not a claim
of generally superior T-count optimisation or superconducting-hardware improvement.

## Precisely proved class

Let c be a control wire, D_c any diagonal one-qubit phase (Z, S, SDG,
T or TDG), and c != t. With
CNOT(c,t) = |0><0|_c tensor I_t + |1><1|_c tensor X_t,
and D_c = d0|0><0|_c + d1|1><1|_c,
one has D_c CNOT(c,t) = CNOT(c,t) D_c. This follows by direct
multiplication of the two orthogonal control projectors.

Such a phase also commutes with CZ, with another diagonal gate, and with
disjoint-support gates. It need not commute with a CNOT with target c,
H or X on c, or a SWAP involving c. The phase optimiser moves a
right-hand single-qubit Z-axis phase left across exactly these cases,
and only to expose a reduction. It is NOT a general phase-polynomial
or ZX-calculus optimiser.

For ANY length-m word W of CNOTs controlled by c (and optionally CZ or
disjoint gates), T(c) W TDG(c) = W as a complete operator including
global phase. This removes two T-type gates. With a single bridging
CNOT, the preceding adjacent and disjoint policies cannot remove them;
the new policy can. The strict algorithmic advantage is only relative
to this repository's older strategies on an exactly characterised
infinite family, NOT relative to Qiskit, PyZX, TKET, VOQC or other tools.

Each phase swap is an exact gate identity. Each rewrite reduces gate
count. Swaps only occur immediately before a reduction is exposed;
at most 64 reductions and at most 63 preceding swaps each ensure
termination under the 64-gate grammar. Exact Python replay checks
operators after every step and the final full operator. The v3 trace
distinguishes commute_phase from commute_disjoint and rejects forgeries.

All rewrite rules preserve or decrease T-count relative to the INPUT.
This does not prove that v3 is always at least as good as v2 on every
input (the greedy pairing order may matter), global T optimality, or
smaller T depth.

## Reproduce actual code

    python -m physqed_q compile examples/phase_control.json --optimizer phase --output /tmp/phase-v3.json
    python -m physqed_q verify /tmp/phase-v3.json
    python -m benchmarks.phase_suite
    python -m unittest tests.test_phase_optimizer tests.test_phase_benchmark -v

The positive input T(0), CNOT(0,1), TDG(0) becomes CNOT(0,1)
(three to one gates, two to zero T gates). The target-side negative
T(1), CNOT(0,1), TDG(1) retains its two T gates.

Two-qubit Lean attestation is separately bounded to at most 16 gates
per word and exactly four-column full-operator equality. It is not
an end-to-end proof of Python or hardware correctness.

The internal ablation is selected, deterministic and not representative.
A pinned REAL Qiskit 2.6.1 comparison is also executed in CI:

    python -m benchmarks.qiskit_compare examples/phase_control.json --level 3 --seed 2026 --optimizer phase

No external superiority is claimed without held-out workload measurements.

## Superconducting hardware: a necessary distinction

A T gate is equal up to global phase to RZ(pi/4). On superconducting
devices with virtual frame-change RZ, the rotation can have zero
scheduled duration. Under a simplified native model with d(RZ)=0,
T(control), CNOT, TDG(control) and its reduced one-CNOT output
have the SAME physical two-qubit gate count and scheduled duration.
Logical T savings are not evidence of a physical speed or fidelity gain.

A physical test would require a specific dated backend Target,
coupling graph, calibrated native operations, scheduling, errors,
held-out circuits, matched Qiskit/TKET baselines and actual
measurement or a declared calibrated simulator.

References for prior art and physical cost:
- https://pyzx.readthedocs.io/en/stable/simplify.html
- https://quantum.cloud.ibm.com/docs/guides/transpiler-stages
- https://quantum.cloud.ibm.com/docs/en/ibm-quantum-compute/qpu-information
