# PHYSQED-Q: two-qubit reproducibility note for Yangsen Ye (15 November 2026)

**Source:** [PHYSQED-Q](https://github.com/tonynewton79-web/PHYSQED-Q), declared **v0.6B**; baseline `main` commit `99a7a35a99766722a7659b55270294967bf32260`. This example is on branch `feature/receipt-ye-two-qubit-20261115`; pin the corresponding pull-request **head SHA** when reproducing. The receipt formats are `physqed-q-exact-receipt-v1` (adjacent optimizer), and the optional Lean attestation format is `physqed-q-lean-theorem-attestation-v2`. The Lean toolchain is pinned to **Lean 4.24.0** by `lean-toolchain`; the exact compiler GitHub Actions workflow exercises Python **3.11 and 3.12**. The repository is a software prototype, not a quantum-processor demonstration.

## Reproduce directly from GitHub

```bash
git clone https://github.com/tonynewton79-web/PHYSQED-Q.git
cd PHYSQED-Q
git fetch origin feature/receipt-ye-two-qubit-20261115
git checkout feature/receipt-ye-two-qubit-20261115
git rev-parse HEAD
python3 -m unittest discover -s tests -p test_ye_repro.py -v
python3 -m physqed_q compile examples/optimize.json --output /tmp/ye-valid.json
python3 -m physqed_q verify /tmp/ye-valid.json
```

The `test_ye_repro.py` test file executes **the actual public compiler and receipt verifier**. With Lean 4.24.0 installed, additionally run:

```bash
PHYSQED_Q_LEAN_BIN="$(command -v lean)" python3 -m unittest discover -s tests -p test_ye_repro.py -v
python3 -m physqed_q.lean_certificate /tmp/ye-valid.json --lean lean --emit-lean /tmp/ye-valid.lean --output /tmp/ye-lean-attestation.json
```

The branch's `lean-receipts.yml` workflow runs these tests with an actual pinned Lean binary on GitHub Actions. Without Lean installed, the two real-Lean tests are **SKIPPED**, not claimed to have passed.

## Three requested outcomes

| Case | Exact circuit / perturbation | Expected result |
| --- | --- | --- |
| **A. Valid 2-qubit rewrite** | `H(0), Z(0), H(0), CNOT(0,1), CNOT(0,1), T(0), T(0)` | `X(0), S(0)`; 7 to 2 gates; T count 2 to 0; steps `HZH_to_X`, `CNOT_inverse`, `TT_to_S`; Python `verified=true`, `rewrites_checked=3`. Optional Lean theorem **accepts** equality of all four columns. |
| **B. Deliberately wrong rewrite** | Replace output with `Z(0), S(0)` instead of `X(0), S(0)`, while also **recomputing** output metrics and the complete receipt SHA-256 | Python receipt verification raises `CertificateError: output differs from trace`; independent exact matrices differ. Corresponding deliberately wrong generated Lean theorem is **rejected** by Lean. |
| **B2. Correct operator, forged rewrite history** | Keep the **correct** `X(0), S(0)` output but change the first receipt rule label from `HZH_to_X` to `HXH_to_Z`; recompute SHA-256 | Python raises `CertificateError: rewrite trace mismatch`, **despite exact equality of source and target full operators**. This extra provenance check is not supplied by a plain unitary comparison. |
| **C. Unsupported input** | `RZ(0)` with an unspecified angle (not part of the discrete gate alphabet) | `CircuitError: gate 0 unsupported`; **no certificate**. A raw Lean gate `("RZ", [0])` likewise fails to decode and cannot prove the theorem. |

An additional negative test submits a well-formed **three-qubit** circuit: Python exact replay accepts it, but the **two-qubit Lean receipt bridge refuses** it with `LeanBridgeError: Lean receipt bridge currently supports exactly two qubits`. This differentiates a bounded supported Python case from an unsupported Lean-attestation request.

## What does the certificate establish beyond direct exact-unitary comparison?

For a supported circuit, Python independently (in a separate call) validates the untrusted JSON, enforces strict field and scope checks, replays the *specific deterministic leftmost rewrite sequence*, checks **full exact** `2^n × 2^n` operators **after each step**, checks that the output agrees with the trace, and recomputes gate/depth/T-gate metrics and the operator fingerprint. It compares algebraic coefficients in `Q(√2,i)` without floating-point tolerance and does **not** discard global phase. A recomputed public SHA-256 is **not** proof of correctness or an authenticity signature; case B tests this distinction.

The separate bounded Lean checker uses the source files `formal/GateIdentities.lean`, `formal/TwoQubitSemantics.lean`, and `formal/RawGateBridge.lean`. Raw gate-name and ordered-index lists are decoded **inside Lean**; a generated theorem asserts exact **four-column (4×4) operator equality** and is accepted only when Lean 4.24.0 compiles it. The gate-identity catalogue also has independently checked exact identities. The optional report states `lean_theorem_checked=true` and `lean_gate_decoder_checked=true`, **not** `python_compiler_end_to_end_formalized=true`.

**Limitations:** the Python semantics, renderer, JSON parsing, optimizer algorithm, source-code provenance and mapping between physical pulses and ideal gates are *not* formally verified end-to-end in Lean. Standard Python receipts intentionally state `lean_kernel_verified=false`. There is no noise, measurement, pulse, hardware fidelity, coupling-graph, scheduling, arbitrary-angle or quantum-advantage certificate. Lean's finite exact theorem is valuable logical corroboration, but this is **not** a general correctness proof for the software stack.

## Research question relevant to superconducting quantum processors

**Can a connectivity-aware compiler for 2–4 superconducting qubits use replayable exact logical rewrite certificates to prevent incorrect native-gate translation, while maintaining a separate, calibration-informed cost model?** The current example isolates the logical-correctness layer. A later joint study would need a clearly specified transmon native gate set, coupling graph, calibrated error/time parameters, a verified translation semantics (including any approximation budget), and measured circuit statistics. PHYSQED-Q presently has *none* of those physical guarantees; the opportunity is to use formal logical checks as an auditable component of an otherwise hardware-calibrated optimisation pipeline.

Maintainer: Tony Newton, Newton Astro Labs, London, UK.
