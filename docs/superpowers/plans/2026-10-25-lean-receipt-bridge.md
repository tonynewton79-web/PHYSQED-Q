# Restricted Lean receipt bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans task-by-task. Steps are checkboxes.

**Goal:** Export exact two-qubit circuit receipts as actual Lean-checkable full-operator theorems.

**Architecture:** `formal/TwoQubitSemantics.lean` builds four-column complete circuit operators over the existing formal scalar algebra. `physqed_q/lean_certificate.py` is a fail-closed JSON-to-Lean generator and subprocess proof checker, while an independent test suite verifies true, false, and malformed circuits.

**Tech Stack:** Lean 4.24.0 core and Python 3.11+ standard library, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-10-25-lean-receipt-bridge.md`

## Global constraints

- Preserve the original receipt schema and `lean_kernel_verified=false` field.
- No external quantum or Python packages required.
- Lean must compile the *generated theorem* itself, not merely the helper gate catalogue.
- Restrict to two qubits and a documented finite gate budget.

## Review focus

1. Control/target reversal in CNOT and qubit-endianness.
2. Incorrect phase or conjugation in S/T adjoints.
3. A changed receipt, fabricated digest, or unbounded circuit reaching Lean generation.
4. False Lean theorem or omitted output gates passing as verified.
5. Absent/wrong-version Lean executable and timeout behavior.

### Task 1 — Four-column exact Lean semantics

**Files:** `formal/TwoQubitSemantics.lean`, `formal/ReceiptWitness.lean` (test fixture).

- [ ] Write one deliberately false operator equality theorem and verify compiler rejection.
- [ ] Define 2-qubit state, all 10 gate actions, `run` and four-basis `operator`.
- [ ] Compile actual seven-gate witness and false-gate fixture with Lean 4.24.0.
- [ ] Add a separate workflow job compiling formal semantics and witness.

### Task 2 — Receipt-specific exported certificate

**Files:** `physqed_q/lean_certificate.py`, `tests/test_lean_certificate.py`.

- [ ] Write failing tests for deterministic rendering, unsupported scope, tampering, false theorem, and real Lean compiler execution.
- [ ] Implement strict rendering, bounded subprocess Lean check, and truthful scoped report.
- [ ] Verify red-green tests, full Python suite, and Lean compilation.

### Task 3 — Documentation and draft release

**Files:** `README.md`, `formal/README.md`, `.github/workflows/lean-receipts.yml`.

- [ ] Document exact guarantees and explicit unverified bridges.
- [ ] Run final Python/Lean verification and negative controls.
- [ ] Publish only on stacked feature branch and open draft PR; do not merge while CI is queued.
