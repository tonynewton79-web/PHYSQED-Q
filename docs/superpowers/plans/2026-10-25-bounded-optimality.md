# Bounded one-qubit optimality implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Certify minimum one-qubit gate count in a declared finite search, beyond ordinary circuit equivalence.

**Architecture:** A dedicated Python exact enumerator chooses a representative; a logically independent exhaustive checker re-enumerates all declared words before validating an untrusted proof receipt. CLI commands expose the separate bounded proof family without changing the v1/v2 compiler or HTTP service.

**Tech Stack:** Python 3.11+ standard library, exact `physqed_q.kernel` arithmetic, `unittest`, GitHub Actions; no new mandatory dependencies.

**Spec:** `docs/superpowers/specs/2026-10-25-bounded-optimality-design.md` (a bounded Milestone A2 refinement of `2026-10-25-certified-optimizer-platform-design.md`).

## Global Constraints

- Fix alphabet to ordered `("H", "X", "Z", "S", "SDG", "T", "TDG")`; allow only a **single qubit**, source length 0–64, integer horizon 0–5.
- Compare exact **full** unitaries in `Q(sqrt(2),i)`; do not quotient global phase.
- Primary objective is **total gate count**, then T/TDG count, then the fixed alphabet's lexicographic word order; one-qubit depth equals gate count.
- Exhaustive complete finite search includes the empty word; declared size `sum(7**k for k in range(h+1))` (19,608 at five) must be recomputed in the verifier.
- Reject unrepresentable operators and forged or unbounded receipt shapes; do not return a verified heuristic or trust a hash as proof.
- Preserve all existing `compile_circuit`, `verify_receipt`, CLI defaults, UI and optional Lean claim boundaries; do not merge or deploy.
- No rank/superiority claims in GitHub.

## Review Focus

1. Fake shorter or costlier representative signed with a recomputed SHA must fail (`test_rehashed_nonminimal_winner_rejected`, Task 1).
2. Equivalent operators only up to global phase must not match (`test_global_phase_not_quotiented`, Task 1).
3. Invalid type/length or deeply nested untrusted receipt fields must fail **before** hashing (`test_unbounded_receipt_rejected_before_hashing`, Task 1).
4. Horizon 0, negative/over-five, `True` and float bounds need exact gatekeeping (`test_horizon_edges`, Task 1).
5. Legacy CLI receipts must remain unchanged; new unsupported search is failure rather than false success (`test_cli_optimality_round_trip`, Task 2).

---

### Task 1: Exact finite search and independent untrusted-certificate checker

**Files:**
- Create: `physqed_q/optimality.py`
- Create: `tests/test_optimality.py`

**Interfaces:**
- Consumes: `kernel.validate_circuit`, `kernel.unitary`, `kernel.unitary_digest`, `kernel._apply`, `kernel.ZERO`, `kernel.ONE`, `compiler.CertificateError` and `compiler._hash`; no modifications to their behavior.
- Produces: `certify_optimality(raw, *, horizon=5) -> dict`, `verify_optimality(receipt) -> dict`, `OptimalityError(ValueError)`.
- Certificate schema: `physqed-q-bounded-optimality-v1` with exact top-level keys `schema/input/optimized/search/operator_sha256/scope/receipt_sha256`.
- `search` keys: `alphabet`, `horizon`, `objective`, `words_examined`, `minimum_gates`, `t_gates`. `scope` must state exact bounded minimum semantics and false Lean/hardware/advantage flags.
- Freeze `search.objective` to `["total_gates", "t_gates", "alphabet_lexicographic"]` and the literal five-field scope specified in the design. Output preserves `input.name`. Verify strict built-in types (not subclass coercion) for all scalar, array and map leaves before hashing.

- [ ] **Step 1: RED** Add `test_hxh_shortest_single_gate` and `test_identity_zero_gates` requiring exact winner, declared size 19,608, own receipt schema and verified minimality. Run `python3 -m unittest tests.test_optimality -v`, observe missing module/function failure.
- [ ] **Step 2: GREEN** Implement `certify_optimality(raw, *, horizon=5)` with a deterministic *length-layered* exhaustive enumeration over the stated ordered alphabet, reusing exact kernel semantics; retain the first minimum cost key `(length, T_count, gate_index_tuple)`. Fail if no operator matches within horizon. Return fixed-scope integrity-digested receipt only after `verify_optimality` succeeds.
- [ ] **Step 3: GREEN checker** Implement `verify_optimality(receipt)` as a separate untrusted-receipt validator and **independent** depth-first or direct-product exhaustive enumeration, not a call back to the planner/table. Reject extra, missing, malicious or nested fields before any JSON digest; enforce canonical source/output and exact operator equality; recompute each enumerated candidate and minimum cost; compare winner, count, scope and claimed cost; return verified true only at the end.
- [ ] **Step 4: RED→GREEN adversarial** Add the five Review Focus tests one at a time, plus `test_unrepresentable_operator_fails_closed`, `test_checker_independent_of_planner` (monkeypatch the planner's enumeration/search helper to emit a wrong answer; checker rejects a validly rehashed false claim), `test_complete_enumeration_even_on_identity` and exact fixtures pinning **T-count** and fixed-alphabet order when minimum length ties. For each new behavior, observe the expected test failure before writing production fixes; rerun the targeted test after repair.
- [ ] **Step 5: Verify** `python3 -m unittest tests.test_optimality -v`, `python3 -m unittest discover -s tests`, `git diff --check`, with a true test count/skip count. Commit `feat: certify bounded one-qubit gate-count optimality`.

### Task 2: CLI demonstration, regression docs and CI

**Files:**
- Modify: `physqed_q/__main__.py`
- Modify: `README.md`
- Modify: `.github/workflows/physqed-q.yml`
- Create: `examples/optimality.json`
- Modify: `tests/test_cli.py`

**Interfaces:**
- Consumes: Task 1's `certify_optimality`, `verify_optimality`, `OptimalityError`.
- Produces: `python3 -m physqed_q synthesize INPUT --horizon 5 [--output RECEIPT]` and `python3 -m physqed_q verify-optimality RECEIPT` with correctly labeled search limitations and nonzero failure on unsupported target.

- [ ] **Step 1: RED** Add `test_cli_optimality_round_trip` proving `H X H` compiles to one-gate winner and verifies separately, `test_cli_optimality_rejects_out_of_scope` covering invalid horizon/unrepresentable source, and regression for legacy `compile`/`verify`. Run `python3 -m unittest tests.test_cli -v`, observe missing subcommand failure.
- [ ] **Step 2: GREEN** Add `synthesize` / `verify-optimality` dispatch and strict numeric `--horizon` validation; reuse existing 256 KiB JSON loader, output conventions, error-to-exit-code mapping. No new default compile optimizer or HTTP change.
- [ ] **Step 3: Document** Create `examples/optimality.json` and concise README section with exact theorem, gate set, horizon cap, command examples, quantitative enumerated word count, failure semantics, and distinctions from equivalence/Lean/hardware proof.
- [ ] **Step 4: CI** Add full optimality unit tests and an independent CLI roundtrip to `.github/workflows/physqed-q.yml`; keep existing matrices and optional skips unchanged.
- [ ] **Step 5: Verify and commit** Run full Python suite, `node tests/test_web_ui.mjs`, `node --check physqed_q/web_assets/app.js`, `python3 -m physqed_q synthesize ...` and separate replay, `git diff --check`; commit `feat: expose bounded optimality proofs in Python CLI and CI`.

### Task 3: Final independent whole-branch review and handoff

**Files:** no feature files unless a reviewed defect needs a test-first repair.

- [ ] **Step 1:** Review fresh full branch diff with independent high-judgment reviewer for scope, exhaustive completeness, adversarial receipt inputs, denial-of-service caps, legacy compatibility and proof wording.
- [ ] **Step 2:** Fix any Critical/Important findings in a fresh RED→GREEN loop with scoped re-review, then independently rerun full tests and check the clean branch.
- [ ] **Step 3:** Prepare a stacked **draft** PR against the v0.6A branch after remote ancestry and base checks; no `main` merge. Report exact tests, skipped optional tools, remote CI state, and limitations. Email only if separately requested.
