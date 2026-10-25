# A formally checked *rule catalogue*, not an end-to-end Lean verifier

`GateIdentities.lean` contains exact statements and proofs for the rewrite
catalogue used by PHYSQED-Q's Python optimizer. It is compiled with Lean 4.24.0
without Mathlib, external axioms, `sorry`, `admit`, or `native_decide`.

The one-qubit scalars use four exact rational coordinates representing
`(a+b√2)+i(c+d√2)`. Each rational is a numerator/positive-denominator pair;
the concrete gate constants start with positive denominators, and addition
and multiplication preserve positivity. Coefficient equality is tested by
integer cross-multiplication; 2×2 matrices compare all entries, not a single
input state. The compiled examples establish H²=X²=Z²=I, inverse pairs,
S²=Z, SDG²=Z, T²=S, TDG²=SDG, HZH=X, and HXH=Z.

For two-qubit gate pairs, the file additionally checks both directional CNOT
involutions, SWAP involution, and CZ's sign-bit involution over Boolean
computational-basis states.

To check locally after installing the toolchain from `lean-toolchain`:

```bash
lean formal/GateIdentities.lean
```

**Trust boundary:** this proves closed gate-algebra claims *in the stated Lean
definitions*. It does not prove equivalence of arbitrary Python circuits,
correctness of JSON parsing or compilation, kernel checking of user receipts,
equivalence of the Lean and Python implementations, quantum speedup, or
physical hardware. In particular, `lean_kernel_verified` in existing JSON
receipts remains `false`. No user should infer a Lean-backed per-receipt
certificate from the presence of these theorem files.

## Two-qubit circuit-specific theorems (v0.3 branch)

`TwoQubitSemantics.lean` adds an exact four-component state representation
with the full ten-gate PHYSQED-Q alphabet on two qubits. The complete
operator is the four-tuple of all four computational-basis output columns.
It includes checks for both CNOT orientations, SWAP, CZ's negative phase,
and both Hadamard qubit locations.

`ReceiptWitness.lean` is a compiled concrete theorem for the seven-gate
example. More importantly, `physqed_q/lean_certificate.py` can deterministically
turn a *validated* two-qubit JSON receipt of at most 16 gates into its own
Lean theorem, compiling the actual generated theorem against freshly compiled
formal definitions before returning a positive report.

```bash
python3 -m physqed_q compile examples/optimize.json --output /tmp/physqed_receipt.json
python3 -m physqed_q.lean_certificate /tmp/physqed_receipt.json \
  --lean lean --emit-lean /tmp/physqed_receipt.lean \
  --output /tmp/physqed_attestation.json
```

The second command **requires a trusted Lean 4.24.0 installation** and returns
an error if it is unavailable, has the wrong version, or rejects the theorem.
The attestation contains the receipt hash, generated-source hash, formal-source
hashes, compiler version, and `lean_theorem_checked=true`. It has no digital
signature and does not turn the original Python receipt's
`lean_kernel_verified=false` into true. The translation into Lean and the
Python interpreter have not been proved sound *inside Lean*; the genuine Lean
claim is equality of the full four-column operators in the published formal
semantics for the explicitly generated gate words.
