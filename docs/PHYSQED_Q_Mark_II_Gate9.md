# PHYSQED-Q Mark II — Proof-Carrying Physical Routing

**Research implementation by Tony Newton**

**Status:** VERIFIED_RESTRICTED_NATIVE_ROUTER_AND_ANALYTIC_FAULT_ENVELOPE.  
**Live hardware:** NOT ACCESSED.  
**Research pull request:** https://github.com/tonynewton79-web/PHYSQED-Q/pull/30  
**Gate 8 rotation foundation:** https://github.com/tonynewton79-web/PHYSQED-Q/pull/29
**Naming:** The research version is **PHYSQED-Q Mark II**. The inherited Python import paths containing `vnext_*` are compatibility identifiers, not a public product name.


## Executive result

Mark II is an independent, dependency-free Python physical routing
implementation. It starts from the validated PHYSQED-Q Gate 8
rotation-certificate compiler and produces an actual native gate
sequence obeying a DECLARED target graph. It does not call Qiskit,
PyZX, Aer or a historical IBM fake device.

The same 19 externally authored PNNL QASMBench sources frozen in
Gate 7 were independently retrieved and verified by Git blob hash.
Of these, 15 meet the Gate 8 logical input policy and four remain
explicitly refused. All 15 were physically mapped onto two
declared synthetic line-device target alphabets (SWAP-native and
bidirectional-CNOT-only), under two different fixed final
physical-readout assignments, generating **60 routed circuit
certificates**. The independent numerical oracle checked each
entire 2^n-by-2^n unitary after applying the known final wire
permutation. The independent ledger auditor verified all 60,
including all 160 explicitly inserted routing SWAPs, final
measurements and exact rational noise bounds.

Native physical circuit benchmarks represent declared
mathematical models, not measured QPU fidelity or proof of superiority
over established hardware-aware compilers.

## Proof-carrying routing model

The input consists of:
- a PHYSQED-Q Gate 8 rational-pi source program (at most 4 qubits
  and 64 source operations);
- a physical native gate alphabet, exact undirected coupling graph,
  and nonnegative zeroed legacy fault fields;
- a separate site/edge/readout marginal fault upper envelope;
- injective initial logical-to-physical assignment;
- explicit classical-bit-to-logical-qubit mapping;
- mandatory physical measurement locations for each classical output.

The Gate 8 rotation lowering step is run against a **declared virtual**
complete graph, strictly as a mathematical intermediate. Its resulting
logical gates are then physically routed; the complete all-to-all
graph is *not* a processor assertion.

For a current physical-token assignment L and nonadjacent
two-qubit gate (i,j), Mark II uses exhaustive breadth-first search
over the finite physical placement states to find a minimum-SWAP
path to any state where {L(i),L(j)} is a declared physical edge.

Every inserted physical SWAP:
- is emitted as SWAP on an allowed edge if the target supports SWAP; or
- is expanded exactly into CNOT(a,b), CNOT(b,a), CNOT(a,b) when
  **both CNOT directions** are stipulated by the undirected coupling model.

The token assignment is updated after each routing SWAP. Logical
SWAP gates themselves remain logical operations and do not silently
alter the compiler's wire-label mapping.

After the last gate, a second breadth-first search moves the
logical output tokens into the explicitly requested physical
measurement sites. Every native operation and every physical output
measurement is recorded in the receipt.

**Optimality scope:** each BFS route minimizes the number of inserted
physical SWAPs for the given *current* obligation, with deterministic
tie-breaking. The whole circuit is not globally minimized for
gate count, native two-qubit count, depth, execution time, or noise.

The full physical operator identity follows inductively from the
permutation conjugation rule of a SWAP and gate-wire relabeling.
The separate dense-complex independent numerical oracle checks the
complete physical operator on all basis inputs for the tested
instances, not just |0...0>. This mathematical identity is established
prior art; the contribution is the tested, bounded software
integration and receipt architecture, not a new theorem about SWAPs.

## Physical noise envelope: robust against unspecified correlations

Every executed native 1Q gate, native 2Q gate, and final measured
output has an explicit modelled marginal fault-event probability
upper bound. For the actual output native gate ledger, let
p_{1,q} denote the declared bound for a single-qubit operation
on physical q; p_{2,ab} for any two-qubit native operation
on physical edge {a,b}; and r_q for a measurement at q.

**No independence between fault events is required:**

    P(at least one fault) <=
      min(1, sum_native1Q p_{1,q}
             + sum_native2Q p_{2,ab}
             + sum_measured r_q).

Under the stated coupling assumption that no fault means the
specified ideal operator is executed, and with the Alpha
projective approximation bound E_logical,

    TVD(P_actual, P_ideal) <= min(1,E_logical+E_fault).

These are **conditional mathematical bounds**, not measured error
rates, standard-QPU noise predictions or verified device
calibrations. Correlated faults are permitted within the
marginal-event model; coherent errors must first be justified as
events with valid marginal probabilities. Nothing in this
engine independently proves a real processor satisfies those
assumptions.

The illustrative case uses distinct exact rational one-qubit,
two-qubit edge and readout fault ceilings. Its numbers were authored
as synthetic stress-test inputs, not extracted from actual IBM
processor calibration.

## Original externally published PNNL benchmark

Original PNNL QASMBench repository:
https://github.com/pnnl/QASMBench
(source commit 357b942396d5c2b7cbc1c229c585a6ef5ccaebac).
All 19 upstream source Git blob SHA-1 values remain frozen in
benchmarks/gate7_qasmbench.py. The original QASM source text
is **not redistributed** in the GitHub release packet.

Own Mark II target models:
1. a chain graph with native SWAP (one native 2Q operation per
   routing swap);
2. the same chain graph without native SWAP, where every routing
   swap is exactly three bidirectional native CNOTs.

Both are **declared synthetic targets**. Neither is an actual
IBM FakeManila/FakeLagos backend. Final measured-output layout
is either identity or reverse.

| Pinned external original | Native-SWAP target, ascending, native 2Q | 3-CNOT-SWAP target, ascending, native 2Q |
| --- | ---: | ---: |
| adder_n4 | 18 | 34 |
| bell_n4 | 13 | 25 |
| qaoa_n3 | 10 | 18 |
| fredkin_n3 | 10 | 14 |
| cat_state_n4 | 3 | 3 |

These are **native instruction counts for distinct gate sets**, not
a physical-performance comparison or a claim of greater compiler
quality than Qiskit or PyZX.

The remaining refused external sources are: basis_trotter_n4
and dnn_n2 (exceed 64 logical source-gate proof budget),
inverseqft_n4 (unsupported whole-register/dynamic operations),
and qft_n4 (controlled-U1 not currently supported).

The separate Alpha QASM importer still provides rational Machin
bounds on literal decimal-radian to rational-pi conversion. Mark II
performs exact routing on that imported rational-pi logical program.
The external audit adds the original-source import bound separately;
it must not be silently treated as zero.

## Reproduce independently

From a checkout of the Mark II branch, without installing any
third-party Python libraries:

    python -m unittest tests.test_vnext_mark2 tests.test_vnext_rotations tests.test_vnext_qasm -v
    python -m physqed_q.vnext_mark2_cli demo --output mark2-own-line.json
    python -m physqed_q.vnext_mark2_cli verify mark2-own-line.json

To rerun the 19-source external suite, the same original
QASMBench files are downloaded by their pinned upstream commit
and checked against their Git blob SHA-1:

    python -m benchmarks.vnext_mark2_external \
      --download --sources /tmp/qasmbench-sources \
      --output /tmp/mark2-external.json
    python -m benchmarks.vnext_mark2_audit \
      /tmp/mark2-external.json \
      --sources /tmp/qasmbench-sources \
      --output /tmp/mark2-audit.json

The external download requires network access for original
public source files; native compilation does not.

## Verification boundaries

- Tests on Python 3.11 and 3.12 passed with NO external quantum
  package installed.
- 40 randomized 2–4-qubit complete-operator comparisons passed.
- Adversarial and correctly rehashed forged receipt claims were refused.
- Original 19 external circuits: 15 admitted / 4 refused.
- Full physical unitary audits: 60/60 passed.
- Physical routing SWAP actions: 160 across the matched test matrix.
- Independent native ledger and exact rational fault bound audit passed.
- SHA-256 receipt digest detects accidental or adversarial document
  changes without a trusted signing key. It is NOT an authenticated
  digital signature.
- No real quantum computer, experimental shots, live calibration
  or hardware noise measurements were used.
- No established novelty claim against sophisticated hardware-aware
  routing (including SABRE or exact global-layout solvers).
- The physical target presently requires the same number of physical
  and logical qubits; ancilla-aware routing, directed couplings,
  gate-specific directional latencies, hardware pulse compilation,
  calibration authenticity, and globally optimal layout remain open.

## Next upgrade

Mark III should add independently authenticated calibration ingestion,
per-direction and per-gate physical costs, an exact small-device global
routing baseline, real measurement outputs and confidence intervals.
These additions require rigorous error and data provenance; synthetic
or historical models must never be relabeled as QPU evidence.
