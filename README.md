# PHYSQED-Q v0.6B — exact quantum-circuit compiler and verification workbench

[![Exact compiler CI](https://github.com/tonynewton79-web/PHYSQED-Q/actions/workflows/physqed-q.yml/badge.svg)](https://github.com/tonynewton79-web/PHYSQED-Q/actions/workflows/physqed-q.yml)
[![Lean gate identities](https://github.com/tonynewton79-web/PHYSQED-Q/actions/workflows/lean-gates.yml/badge.svg)](https://github.com/tonynewton79-web/PHYSQED-Q/actions/workflows/lean-gates.yml)
[![Lean receipt witnesses](https://github.com/tonynewton79-web/PHYSQED-Q/actions/workflows/lean-receipts.yml/badge.svg)](https://github.com/tonynewton79-web/PHYSQED-Q/actions/workflows/lean-receipts.yml)
[![Optional Qiskit comparison](https://github.com/tonynewton79-web/PHYSQED-Q/actions/workflows/qiskit-compare.yml/badge.svg)](https://github.com/tonynewton79-web/PHYSQED-Q/actions/workflows/qiskit-compare.yml)

**Canonical project repository:** [tonynewton79-web/PHYSQED-Q](https://github.com/tonynewton79-web/PHYSQED-Q). Source code, reproducible examples, independent tests, and verification workflow are maintained here.

An independent module of Tony Newton's PHYSQED programme, implemented as a **bounded, exact quantum software prototype**. It transforms gate sequences using a small specified rule catalogue, recomputes complete operators in Q(√2,i), and emits self-contained evidence that a separate invocation can replay. This is not a quantum processing unit or a claim of quantum speedup.

## Bounded exact one-qubit optimality (v0.6B research capability)

The separate `synthesize` command exhaustively searches the ordered alphabet
`(H, X, Z, S, SDG, T, TDG)` through a declared integer horizon `0 <= h <= 5`
(default 5), including the empty word. Input is exactly one qubit with at most
64 gates from this alphabet. A successful receipt certifies the following:
among all words of length at most `h` with the same **full exact operator**
in Q(√2,i), the winner minimizes, lexicographically,
`(total gate count, T count, alphabet-order word)`. T and TDG each cost one
T gate; the last tie-break follows the declared alphabet, not Unicode order.
On one qubit, gate count also equals circuit depth.

```bash
python3 -m physqed_q synthesize examples/optimality.json --horizon 5 --output /tmp/physqed-q-optimality.json
python3 -m physqed_q verify-optimality /tmp/physqed-q-optimality.json
python3 -m unittest tests.test_optimality tests.test_cli -v
```

This deterministic witness transforms `H X H` into the one-gate word `Z`.
Both generation and independent replay account for every word:
`N(h) = sum(7**k for k in range(h+1))`, or **19,608 cases at horizon 5**,
even when a zero-gate identity wins. The verifier reruns its own exhaustive
enumeration, relative to the shared exact arithmetic and gate-semantics kernel;
it does not trust the declared winner, count, costs or digest as proof.
If no exact representative exists within the horizon, synthesis rejects with
exit code 2 and emits no certificate or success JSON. Invalid inputs and
tampered receipts likewise reject. Without `--output`, synthesis prints the
receipt directly; with it, the CLI prints the path, digest and equivalence flag.

This is a bounded alphabet-relative minimum, **not a global compiler** or a
claim about alternative gate libraries, ancillas, two-qubit circuits,
approximation, gate latencies or physical hardware. Global phase is exact,
not ignored. The distinct `physqed-q-bounded-optimality-v1` schema explicitly
keeps Lean, hardware and quantum-advantage flags false; the digest detects
corruption, not authenticity. It is not Lean certification of the search or
kernel. Ordinary `compile`/`verify`, legacy receipts, the loopback HTTP API and
public UI are unchanged. No additional runtime dependencies are required.

## v0.6A: opt-in certified disjoint commutation (development branch)

The default `adjacent` policy and v1 receipt format are unchanged. Select
`commuting` explicitly to emit a v2 receipt: after adjacent reductions, it
can move a gate across gates on disjoint qubits to expose an existing
two-gate reduction. It does not commute overlapping gates or search for a
globally optimal circuit. The workbench has the same opt-in optimizer selector.
To try the witness visually, import `examples/commuting.json` into the editor
and select the commuting strategy before choosing **Optimize & Verify**.

```bash
python3 -m physqed_q compile examples/commuting.json --optimizer commuting --output /tmp/physqed-q-commuting.json
python3 -m physqed_q verify /tmp/physqed-q-commuting.json
python3 -m benchmarks.commuting_suite
```

For this fixture, `H(0), X(1), H(0)` becomes `X(1)`: the adjacent policy
leaves 3 gates at depth 2, while the commuting policy gives 1 gate at depth 1.
Both have T count 0. The verifier independently replays every recorded swap
and reduction, checks the full exact operator after every step and at the
endpoint, and recomputes the metrics. `verify` supports both receipt versions.
The public SHA-256 digest is integrity evidence, not an authenticity signature.

The deterministic [internal benchmark](benchmarks/README.md) also includes
an adjacent-reduction parity case and a blocked overlapping-gate case. These
three selected examples measure only the two internal policies, not general
compiler optimality, hardware fidelity, or an external optimizer comparison.
Runtime remains Python-standard-library-only with the same 0–4 qubit,
64-input-gate bound. Python replay does not invoke Lean or verify hardware;
the receipt flags `lean_kernel_verified` and `hardware_verified` remain false.

## v0.5 visual Python workbench

PHYSQED-Q now has a local graphical interface driven by the actual Python
compiler and replay verifier. It needs only Python 3.11+ and a modern browser:

```bash
python3 -m physqed_q.web --port 8765
```

Open **http://127.0.0.1:8765/** in your browser (or supply `--open` to ask
Python to launch your default browser). On Windows, `py -m physqed_q.web`
also works with a suitable Python installation.

The workbench provides:

- A visual 1–4 qubit editor with all ten supported gate types, including
  explicitly ordered CNOT controls and targets, gate reordering and removal.
- Bell, GHZ and seven-to-two gate examples; import and export of source JSON.
- An **Optimize & Verify** button that runs the real Python compiler and then
  independently replays the complete exact-operator certificate.
- Before/after gate count, circuit depth, T count, rule trace, the optimized
  circuit diagram, operator SHA-256 digest and JSON receipt download.
- An optional **Lean attest** button for supported two-qubit receipts when
  Lean 4.24.0 is installed. Use `--lean /path/to/lean` if not on PATH.

It binds to IPv4 loopback `127.0.0.1` only, rejects cross-origin writes and
untrusted Host headers, and does not upload your circuits to a service. The
visual interface adds no mathematical assumptions: successful replay is still
the exact bounded Python check; Lean remains a separate, explicitly limited
attestation. Neither proves real quantum-hardware behavior.

To check the new HTTP API and JavaScript state behavior:

```bash
python3 -m unittest tests.test_web -v
node --check physqed_q/web_assets/app.js
node tests/test_web_ui.mjs
```

Node is used only to run JavaScript developer tests; the workbench itself has
no Node/npm or third-party Python runtime dependency.

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

## v0.4 research branch: gate decoding moved into Lean

The certificate now renders the original receipt's **gate names and ordered
qubit indices as literal data**, e.g. `("CNOT", [1, 0])`, instead of selecting
Lean gate constructors in Python. The new `formal/RawGateBridge.lean` defines
the entire two-qubit name/arity/index map in Lean. An unknown name, invalid
arity, or invalid index fails decoding and makes the theorem false. Successful
attestations have schema `physqed-q-lean-theorem-attestation-v2`, contain the
decoder file hash, and set `lean_gate_decoder_checked=true` after real Lean
compilation. They still say `python_compiler_end_to_end_formalized=false`.

The verified scope remains **two qubits, at most 16 gates in each receipt
word, exact full-operator equality**; the original Python receipt is unchanged.
This is an independently checkable extension, not a quantum-advantage claim.
