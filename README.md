# PHYSQED-Q v0.1 — exact, replayable quantum-circuit compiler

[![Exact compiler CI](https://github.com/tonynewton79-web/PHYSQED-Q/actions/workflows/physqed-q.yml/badge.svg)](https://github.com/tonynewton79-web/PHYSQED-Q/actions/workflows/physqed-q.yml)

**Canonical project repository:** [tonynewton79-web/PHYSQED-Q](https://github.com/tonynewton79-web/PHYSQED-Q). Source code, reproducible examples, independent tests, and verification workflow are maintained here.

An independent module of Tony Newton's PHYSQED programme, implemented as a **bounded, exact quantum software prototype**. It transforms gate sequences using a small specified rule catalogue, recomputes complete operators in Q(√2,i), and emits self-contained evidence that a separate invocation can replay. This is not a quantum processing unit or a claim of quantum speedup.

## Run (no installation or third-party packages)

From the repository root:

```bash
python3 -m physqed_q demo bell
python3 -m physqed_q demo ghz
python3 -m physqed_q compile examples/optimize.json --output /tmp/physqed-q-receipt.json
python3 -m physqed_q verify /tmp/physqed-q-receipt.json
python3 -m unittest discover -s tests -v
```

`compile` without `--output` prints the JSON receipt directly. `verify` exits 0 only on a full exact replay; invalid input or tampering exits 2 and prints `REJECTED` on stderr.

## First exactly verified optimization

The provided `optimize.json` transforms seven gates into two:

```
H(0) Z(0) H(0) CNOT(0,1) CNOT(0,1) T(0) T(0)
    → X(0) S(0)
```

The verifier replays `HZH_to_X`, `CNOT_inverse`, `TT_to_S`, recomputes the complete unitary operator after every step, and independently checks the final full operator. For this particular example, gate count falls from 7 to 2 and T count from 2 to 0. That is not a general algorithmic benchmark.

## Exact semantics and receipt guarantees

- Single-qubit gates: H, X, Z, S, SDG, T, TDG. Two-qubit gates: ordered CNOT(control,target), CZ, SWAP.
- Qubit zero is the least significant basis bit. 0–4 qubits, at most 64 gates; arbitrary angles, measurements, channels, noise and hardware coupling are intentionally unsupported.
- Amplitudes are algebraic numbers `(a+b√2)+i(c+d√2)` represented by four rational coefficients. Not floating point.
- State evolution is unitary and deterministic; equality is of **complete operators**, not merely one prepared state and not up to global phase.
- A SHA-256 receipt fingerprint detects ordinary modification but is not an authenticity signature; the verifier treats every input as untrusted regardless of digest.
- The gate-depth metric uses greedy earliest scheduling on disjoint qubits; it is not hardware-aware timing.
- The base `compile` and `verify` commands do not invoke Lean; `lean_kernel_verified=false` remains correct for their receipts. The separate optional v0.3 bridge invokes Lean on a bounded generated theorem. No physical hardware is used; `hardware_verified=false` and `quantum_advantage_demonstrated=false`.

The exact evaluator and rewrite patterns are in separate modules; the verifier explicitly checks the semantics of each transformation rather than trusting only pattern names or hashes. The tests include independent expected finite-state amplitudes and adversarial alteration checks. End-to-end formalisation of the Python compiler, larger circuit semantics, noise models, connectivity-aware compilation, and held-out external comparisons remain future development.

## Security and provenance

The CLI accepts data-only JSON. It refuses unexpected fields, noninteger indices, repeated qubits, unsupported gates, oversize inputs, and noncanonical receipts. Inputs never execute code. This module is a clean-room design, not a derivative of the separately reviewed UUIDNA QPU package (published under CC-BY-NC-ND-4.0).

Author: Tony Newton — Newton Astro Labs. Public research prototype; ordinary Python receipts make no Lean-kernel claim, while the optional bounded bridge emits a separately scoped theorem attestation. See [DESIGN.md](DESIGN.md) for scope and acceptance criteria.

## v0.2 research branch: checked gate catalogue and external baseline

The supplementary [Lean proof catalogue](formal/README.md) has a pinned
Lean 4.24.0 compiler check for specific single-qubit identities and
two-bit involutions. This does **not** make Python receipts Lean-verified;
`lean_kernel_verified` remains `false` in each receipt.

An [optional pinned Qiskit 2.6.1 comparison](benchmarks/README.md)
records reproducible ideal gate/depth metrics, fixed transpiler settings,
and exactly which external outputs can be compared under PHYSQED-Q's strict
operator convention. The current selected examples show parity with Qiskit
optimization level 3, **not** a superiority result.

## v0.3 research branch: a Lean theorem for an actual receipt

For a bounded **two-qubit circuit with at most 16 input gates**, the new
bridge generates Lean source explicitly naming the receipt's input and
optimized gate sequences, then compiles a complete four-column operator
equality with the pinned Lean 4.24.0 kernel:

```bash
python3 -m physqed_q compile examples/optimize.json --output /tmp/physqed_receipt.json
python3 -m physqed_q.lean_certificate /tmp/physqed_receipt.json \
  --lean lean --emit-lean /tmp/physqed_receipt.lean \
  --output /tmp/physqed_attestation.json
```

The second command fails if the theorem fails or Lean is missing, and creates
a separate attestation only after successful compilation. [Formal scope and
remaining trust boundary](formal/README.md). This does not constitute a Lean
proof of the Python compiler, nor a signed certificate.
