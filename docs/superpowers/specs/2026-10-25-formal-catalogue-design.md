# PHYSQED-Q v0.2: formal gate catalogue and reproducible comparison

## Intent

Advance the exact quantum compiler by independently kernel-checking its elementary rewrite identities, and enable honest reproducible measurements against an established quantum compiler. The public `PHYSQED-Q` repository remains canonical.

## Selected design

1. **Lean 4 closed algebraic certificates (selected):** encode the same rational-coefficient number field `(a + b√2) + i(c + d√2)` and explicit 2×2 matrices; check the one-qubit identities using Lean reduction. Encode reversible two-bit gate maps and prove involutions by finite decision. This is a finite verified rule *catalogue*, not a verified Python compiler or a bridge authenticating per-circuit receipts.
2. **Qiskit comparison (selected, optional dependency):** use the same input circuits, a fixed native gate alphabet, specified seed/optimization level, and raw gate/depth/T-count metrics. Include exact output verification for supported Qiskit gates; flag unsupported/global-phase cases as not exactly comparable. Record the actual Qiskit version. No advantage claim follows from the harness alone.

Alternatives deferred: a universal Lean matrix implementation with an end-to-end extraction bridge (too broad for this increment), and unverified optimizer-quality claims based on output gate counts alone.

## Scope and integrity constraints

- Keep `compiler.py`'s existing exact semantic recheck and receipt format unchanged.
- Keep receipt field `lean_kernel_verified=false`: compiled Lean lemmas do not prove arbitrary Python execution or bind a receipt to the Lean kernel.
- Lean proofs must contain no `sorry`, `admit`, user axioms, or `native_decide`; CI runs the actual Lean 4.24.0 compiler.
- The formal amplitudes and gate matrices must match `kernel.py` coefficient conventions exactly.
- Qiskit is an **optional** dependency, never required by the standard-library package or its main CI.
- Benchmark metrics are labelled observations for named circuits and settings, never a universal superiority claim. Reject outputs outside PHYSQED-Q's 10-gate alphabet rather than silently dropping gates.
- Preserve `main` until a separate reviewed feature PR has passing tests and formal compilation.

## Acceptance

- Lean checks H²=I, HZH=X, HXH=Z, S²=Z, T²=S, their adjoint squares, and single-qubit inverse pairs with exact full-operator equations.
- Lean checks the CNOT/CZ/SWAP involutions over all ordered Boolean pairs.
- One intentionally false Lean theorem must fail to compile during development (red check); valid source compiles successfully.
- Benchmark harness rejects absent Qiskit clearly; when present, it reports deterministic settings and does not imply numerical results establish proof.
- Python test suite remains green. No changed claims in existing receipts.
