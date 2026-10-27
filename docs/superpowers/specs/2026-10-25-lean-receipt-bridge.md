# Restricted circuit-specific Lean certificate bridge

## Intent

Produce a concrete Lean theorem for the actual input and output circuits in a PHYSQED-Q receipt, and compile that theorem under Lean 4.24.0 before reporting success.

## Approach

- Select a **two-qubit-only, finite-size** initial scope. Model exact amplitudes from the established `GateIdentities.lean`, all 10 existing gates, and the four basis vectors in Lean. Define `operator` as four output columns and prove their extensional equality by closed kernel reduction.
- Python independently verifies its usual receipt first. It then deterministically renders the source and output gate lists as explicit Lean `Gate` constructors; no strings, arbitrary user Lean code, `sorry`, axioms, or trusted assertions are injected.
- A separate Lean bridge compiles the established formal definitions and the generated theorem. Only a successful Lean process yields an attestation that this **specific generated theorem** compiled; failures never yield one.
- Preserve `lean_kernel_verified=false` in the original Python receipts. The bridge outputs a separate report with `lean_theorem_checked=true` and `end_to_end_compiler_verified=false` so there is no ambiguity about the trust boundary.

Alternative: prove a generic arbitrary-qubit compiler sound using a polymorphic formal Hilbert space. This is more general but materially exceeds the first receipt-specific release; continue after a bounded compiled bridge is validated. Another alternative—asserting Python output is verified because local gate lemmas compile—would be unsound and is excluded.

## Validation and safety

- Reject untrusted receipts before rendering; enforce two qubits and a small gate budget.
- Generate exact Lean definitions of the complete input and output operators; avoid assumptions about measured states or global-phase equivalence.
- Prove with ordinary `decide` on explicit integers and fractions; no `native_decide`, `sorry`, or custom axioms.
- An intentionally false circuit equivalence must fail Lean compilation. Test a true optimisation receipt and a nontrivial CNOT orientation case.
- Cap Lean process runtime; verify toolchain version; never execute user-supplied Lean source.
- Do not treat a SHA digest as a signature or as proof that the Python-to-Lean encoding is formally correct.
- Publish as a stacked draft PR targeting the existing v0.2 branch, with a new Lean CI task.
