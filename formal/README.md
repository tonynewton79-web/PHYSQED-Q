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
