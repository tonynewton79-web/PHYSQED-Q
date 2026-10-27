# PHYSQED-Q v0.4 — Lean-native receipt gate decoding

Date: 25 October 2026. Status: implemented prototype, subject to reproducible
Lean and CI checks.

## Goal

Reduce the Python-to-Lean translation trust boundary for two-qubit receipts.
Instead of mapping a received gate to a Lean `QGate` constructor in Python,
render only the literal `(gate name, ordered qubit-index list)` received from
the validated receipt. Perform name, arity and index decoding within Lean.

## Scope and acceptance

1. Preserve existing bounded Python JSON receipt validation and the original
   `lean_kernel_verified=false` flag; reports remain separate.
2. Represent the supported H/X/Z/S/SDG/T/TDG single-qubit gates and
   CNOT/CZ/SWAP two-qubit gates with all valid two-qubit index choices.
3. Reject an unknown name, extra/missing operand, or out-of-range qubit in
   *either* circuit; decoding returns `none` and raw operator equality fails.
4. Use exact four-column two-qubit operator semantics, with a proved bridge
   between the executable Boolean equality and the original Prop equality.
5. Test valid optimizations and invalid/malformed/false operator targets in
   the real Lean 4.24.0 kernel. Bound source and optimized words to 16 gates.
6. Record three compiled formal source hashes in the v2 attestation, and do
   not suggest that a proof of the Python compiler or hardware was obtained.

## Non-goals

Formal JSON parsing, arbitrary gates, measurement, noise, parameterized
rotations, device calibration, circuit routing, Python interpreter semantics,
and authenticated signatures are outside the present theorem.
