# PHYSQED-Q Lean catalogue and comparison Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add genuine Lean-checked bounded gate identities and a reproducible optional external-compiler comparison harness.

**Architecture:** Formal Lean scalar and 2×2 semantics live in `formal/GateIdentities.lean`, separated from Python verifier semantics and claims. An independent optional Qiskit entry point reads existing circuits and reports transparent observed metrics. GitHub Actions runs Lean proof compilation separately from Python CI.

**Tech Stack:** Lean 4.24.0 core; Python 3.11+ standard library; optional Qiskit; GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-10-25-formal-catalogue-design.md`.

## Global constraints

- The main Python package and receipt schema remain unchanged.
- No user axioms, sorry/admit, native_decide, or unverified Lean status flags.
- External compiler is optional and version is recorded.

## Review focus

1. Wrong sign in complex coefficient multiplication: a false Lean identity should fail.
2. Missing normalization of H and T phases: exact identities must fail if factors are changed.
3. CNOT orientation mistakes: involutions must be checked for control 0 and control 1.
4. Qiskit missing or changed API: clear unsupported result, not fabricated statistics.
5. Global-phase-only equivalence: do not treat as exact full-operator equality.

### Task 1: Formal finite gate identities

**Files:** `formal/GateIdentities.lean`, `lean-toolchain`, `.github/workflows/lean-gates.yml`, `formal/README.md`.

**Interfaces:** Lean structures `Exact`, `Mat2` with field operations, `mulMat`, concrete gates `h`, `x`, `z`, `s`, `sdg`, `t`, `tdg`, and theorem names `hzh_eq_x`, `hxh_eq_z`, `t_mul_t_eq_s`, etc.

- [ ] Create a failing Lean theorem for a deliberately false equality, run compiler, confirm failure.
- [ ] Implement exact scalar and matrix operations and true theorem statements.
- [ ] Compile with the pinned Lean toolchain, inspect full success output.
- [ ] Add workflow and documentation of limited theorem scope.

### Task 2: Honest external baseline

**Files:** `benchmarks/qiskit_compare.py`, `tests/test_benchmark.py`, `benchmarks/README.md`.

**Interfaces:** CLI `python -m benchmarks.qiskit_compare examples/optimize.json --level 1 --seed 2026`, machine-readable JSON records with compiler version, settings, comparable flag, input/optimized metrics.

- [ ] Write failing benchmark parsing/invariant tests including optional dependency and non-equivalent/unsupported output conditions.
- [ ] Implement Qiskit invocation with fixed basis, seed, level, and exact output acceptance where possible.
- [ ] Run tests; optionally install/run compatible Qiskit once for real benchmark observations.
- [ ] Document scope and run full Python regression suite.

### Task 3: Review and publish safely

- [ ] Verify Lean file contains no proof placeholders or axioms.
- [ ] Verify compiled Lean proof and entire Python test suite fresh.
- [ ] Compare branch tree to intended files; keep `main` unchanged.
- [ ] Open a draft PR and report the exact CI status; no merge without review.
