# PHYSQED-Q Gate 8 — Certified Rotation Compiler
## A self-contained, proof-carrying rotation compiler with a declared physical fault envelope

**Author:** Tony Newton

### Scope

This is a working new PHYSQED-Q research version, implemented in
standard-library Python. It does NOT replace or weaken the established
v1-v3 exact circuit kernel or its receipt formats. The new components
are separate and opt-in. Some Python filenames retain the historical `vnext_*` prefix solely for import and certificate compatibility; **it is not the system's name**:

- physqed_q/vnext.py — certified, bounded rotation lowering, rational
  global phase, operator-error and conditional physical fault budgets
- physqed_q/pi_interval.py — exact rational brackets for pi from the
  classical Machin arctangent identity
- physqed_q/vnext_qasm.py — owned strict OpenQASM 2.0 subset importer,
  exact source hashes and safe terminal measurement deferral
- physqed_q/vnext_numeric.py — separate standard-library dense-complex
  unitary checker up to four logical qubits
- physqed_q/vnext_cli.py — standalone local compile, verify and demo
- benchmarks/vnext_external_qasmbench.py, benchmarks/vnext_audit.py,
  benchmarks/vnext_qiskit_crosscheck.py — 19-source external evaluation,
  independent rational audit and optional original-QASM numerical comparison

**NO fake IBM backend is used for this Gate 8 mathematical core or its
external source-coverage benchmark.** The declared target is NOT an
experimentally measured device. Real hardware execution remains unavailable
until device access, fresh calibration and measured shots are supplied.

### Mathematical engine

The input rational-pi rotations are RZPI, RXPI, RYPI and U3PI, with
rotation angles encoded by canonical Fraction-compatible strings.
The conventional gate identities used are

    Rx(theta) = H Rz(theta) H
    Ry(theta) = S H Rz(theta) H S^-1
    U3(theta,phi,lambda)
       = exp(i*(phi+lambda)/2) Rz(phi) Ry(theta) Rz(lambda).

The latter phase is **essential for full-unitary semantics**.
Our receipt explicitly records a rational multiple of pi for the
resulting global phase; it is not silently discarded.

If the declared native target accepts RZPI, all these gate
families are lowered with *zero logical approximation error* under
the declared gate model.

If the target does not include native RZPI, the compiler deterministically
rounds each rational-pi angle alpha to k*pi/4 and emits the
corresponding exactly representable Z phase T^k. This is a coarse
bounded-Clifford+T policy, **not** a precision-optimal Ross-Selinger
or RUS synthesizer. The exact operator identity is

    Rz(pi*k/4) = exp(-i*pi*k/8) T^k.

For each requested angle alpha*pi, the rigorous projective
operator-norm bound is

    || Rz(pi*alpha) - exp(-i*pi*k/8) T^k ||_2
       <= pi * |alpha-k/4| / 2
       < (11/7) * |alpha-k/4|.

All local bounds are added through the telescoping product
inequality for unitary matrices. If the total exceeds the declared
max_projective_operator_error, the compiler **REFUSES**.

### Exact handling of literal decimal radians

A QASM expression explicitly written as pi multiplied by a finite
decimal is interpreted as a precisely specified rational multiple of pi.
A bare decimal-radian literal is NOT silently treated as an exact
rational multiple of pi. Instead, the importer constructs q in Q and
a rational error bound from

    pi = 16 arctan(1/5) - 4 arctan(1/239).

Alternating rational arctangent series produce pi_lower and pi_upper
with pi_lower < pi < pi_upper. For a decimal-radian literal theta,
the import certificate stores

    epsilon = max(|theta-q*pi_lower|, |theta-q*pi_upper|)
    |theta - q*pi| <= epsilon.

The projective operator bound for the parameter is epsilon/2.
For U3, the three local bounds add, allowing a free overall phase
in the projective operator comparison; QASM global phases are preserved
in the input-to-native certificate's phase convention.
The end-to-end source-to-native bound adds import and compilation
bounds. The frozen external sweep requires <= 1/1000000.

This is a rigorous logical approximation bound conditional on
the literal QASM number semantics, not a physical gate accuracy claim.

### Our own declared-target interface

An independent target JSON includes:

    name, qubits, native_gates, couplings,
    one_qubit_fault, two_qubit_fault,
    readout_faults, provenance

Provenance is either "synthetic" or "user_supplied". The latter
does **not** mean the calibration is authentic or independently verified.

If each native 1Q location has an independent stochastic fault
probability p1, each 2Q location p2, and each final readout location
probability r_j, a no-fault coupling provides an exact rational upper
bound on output total variation distance:

    E_fault = 1 - (1-p1)^N1 (1-p2)^N2 Prod_j(1-r_j).

It applies only if the declared local stochastic model genuinely
bounds the actual implementation. It does not certify realistic
correlated, coherent, leakage, non-Markovian or calibration-drift
errors. The combined projected worst-case output bound is

    E_total = min(1, E_logical + E_fault).

This is a transparent, conditional upper guarantee. It is not an
empirical QPU fidelity estimate or a substitute for hardware shots.
Nonadjacent native two-qubit gates are REFUSED by this alpha engine;
physical routing automation is a separate future upgrade.

### Reproduction (no third-party Python packages)

Run from the PHYSQED-Q repository root:

    python -m physqed_q.gate8_cli demo --mode native --output gate8-native.json
    python -m physqed_q.gate8_cli verify gate8-native.json --numeric-check
    python -m physqed_q.gate8_cli demo --mode clifford_t --output gate8-clifford-t.json
    python -m physqed_q.gate8_cli verify gate8-clifford-t.json --numeric-check
    python -m unittest tests.test_vnext_rotations tests.test_vnext_qasm -v

A native mode target implements exact logical RZPI; the finite
Clifford+T mode may refuse overly tight error tolerances.
The CLI demonstrations declare their fault numbers as SYNTHETIC
and neither use fake IBM processors nor make real-device claims.

### Published external evaluation, matching Gate 7's locked source list

Original upstream: PNNL QASMBench (Ang Li et al., ACM TQC 2022,
DOI 10.1145/3550488); source revision
357b942396d5c2b7cbc1c229c585a6ef5ccaebac.

Exactly the same 19 original upstream files and content SHA1 checks
are reused. File contents are NOT vendored here, and upstream license
metadata was NOASSERTION in our audit.

| Test | Earlier PHYSQED-Q Gate 7 | New Gate 8 rotation engine |
| --- | ---: | ---: |
| Original, SHA-pinned external QASM files | 19 | 19 |
| Admitted and verified | 10 | **15** |
| Explicitly refused | 9 | **4** |
| Own numeric operator oracle (no Qiskit/Aer/PyZX) | No | Yes |
| Own rational QASM rotation-angle certificates | No | Yes |
| Historical fake IBM backend required for logical acceptance | Gate 7 native benchmarking used them | **No** |

The additional five accepted external workloads are:
basis_change_n3, bell_n4, linearsolver_n3, qaoa_n3, quantumwalks_n2.

All 15 accepted programs have recomputed certified native receipts and
independent dense-complex checks. 26 decimal-radian conversion
witnesses were checked with exact rational pi brackets.
A SEPARATE optional Qiskit 2.6.1 comparison parses the *original*
QASMBench files and checks all 15 full operators up to global
phase; the largest observed floating-point Frobenius discrepancy was
about 7.11e-15. Qiskit is NOT used by the Gate 8 compiler or primary
19-case coverage workflow.

The remaining four refusals have specific reasons:

- basis_trotter_n4: exceeds 64-source-gate proof budget
- dnn_n2: exceeds 64-source-gate proof budget
- inverseqft_n4: unsupported whole-register / mid-circuit control semantics
- qft_n4: unsupported controlled-U1 gate

No silent substitution, approximated conditional gate, or fabricated
QPU result is admitted.

### Independent verification and adversarial coverage

- Deterministic, bounded JSON; canonical Fraction inputs; no Python
  float accepted as certificate input
- Separate Gate 8 receipt schema and self-contained SHA-256 integrity digest;
  the digest is not a digital signature
- Recomputed rotations, phases, cost counts, fault assumptions and
  source-to-target error bounds on verification
- Forged receipt fields and even validly rehashed false hardware claims
  are refused
- Independent dense complex matrix tests, including randomized mixed
  one-/two-qubit circuits
- 19-source original Git SHA-pinned manifest with exact refusal ledger
- Separate Machin-bound rational replay of every decimal-radian witness
- Optional external original-QASM independent Qiskit operator crosscheck

The mathematical gate identities and Machin pi formula are **established
prior art**. This is a useful new version of the PHYSQED-Q SOFTWARE,
not a claim of a new theorem, new quantum mechanics, quantum speedup
or physical compiler superiority. It is not independently Lean proved.

### Next major upgrade after this alpha

1. Improve finite Clifford+T rotation precision with certified
   algebraic/interval synthesis instead of quarter-turn rounding.
2. Incorporate a native device-independent SWAP router with exact
   physical measurement output constraints, without Qiskit dependencies.
3. Accept a signed, timestamped hardware calibration/Target record and
   separately report its authenticity and uncertainty; do not treat
   user-supplied calibration as independently verified.
4. Externally validate on newly unseen circuits and execute
   randomized/interleaved jobs on a REAL quantum processor if such
   access is provided. No fake backend should be represented as
   measured physical data.

**Status: PASS_RESTRICTED_LOGICAL_COMPILER_AND_ANALYTIC_CERTIFICATES.**
**Hardware validation: NOT PERFORMED.**
