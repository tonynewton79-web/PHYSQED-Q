# Certified commuting-gate optimizer implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a more capable, deterministic exact optimizer that reduces gate pairs separated by independent-qubit operations, with independently replayable versioned receipts and repeatable local measurements.

**Architecture:** The existing adjacent-only compiler and v1 receipt schema remain the default and unchanged. An opt-in `commuting` strategy emits a v2 receipt whose trace explicitly records each disjoint-support adjacent swap, followed by an existing exact reduction. The verifier checks each declared move, rejects deviations from a deterministic plan and recomputes full exact operators at every step.

**Tech Stack:** Python 3.11+ standard library, `unittest`, optional Lean 4.24.0 unchanged, existing local HTTP server and vanilla JavaScript UI.

**Spec:** `docs/superpowers/specs/2026-10-25-certified-optimizer-platform-design.md`, §4 (Milestone A), §7–9.

## Global constraints

- No new required Python runtime dependencies; accept only the existing 0–4 qubit, 64-gate exact circuit language.
- Preserve `compile_circuit(circuit)` returning the old deterministic v1 receipt, and preserve verification of all archived v1 receipts.
- Opt-in `compile_circuit(circuit, *, optimizer="commuting")` returns `physqed-q-exact-receipt-v2`, with its own immutable scope value and truthful Lean/hardware flags.
- Exact full operator equality in `Q(sqrt(2),i)` is mandatory before reporting success; no global-phase quotient.
- Public GitHub prose uses verifiable metrics and caveats, not claims of competitive superiority.
- Do not merge branches or deploy to a paid/public hosting service in this plan.

## Review focus

1. **Overlapping operations** must not commute: add `test_overlapping_intervening_gate_blocks_reduction` to Task 1.
2. **CNOT direction** must not be silently reversed: add `test_reversed_cnot_does_not_cancel` to Task 1.
3. **Rehashed forged swap** must be rejected on exact semantics or deterministic trace: add `test_forged_commutation_rejected_after_rehash` to Task 1.
4. **Adversarial maximum length** must stop in finite time: add `test_64_gate_commutation_trace_is_bounded` to Task 1.
5. **Old Lean and API behavior** must not acquire new claims: add `test_legacy_receipts_remain_valid_and_scoped` to Task 1 and `test_web_defaults_to_legacy_opt_in_to_commuting` to Task 2.

---

### Task 1: Versioned exact compiler and untrusted receipt replay

**Files:**
- Modify: `physqed_q/compiler.py`
- Create: `tests/test_commuting.py`

**Interfaces:**
- Consumes: existing `validate_circuit`, `unitary`, `unitary_digest`, `_replacement`, `_step`, `metrics`, `verify_receipt`.
- Produces: `compile_circuit(raw, *, optimizer="adjacent") -> dict`, `verify_receipt(receipt) -> dict` accepting v1 and v2.
- V2 schema: `physqed-q-exact-receipt-v2`; additional rule `commute_disjoint` uses existing trace step keys `rule/index/before_sha256/after_sha256`.
- Bound: at most `MAX_GATES * MAX_GATES + MAX_GATES` v2 trace steps, with explicit `CertificateError` on excess.

- [ ] **Step 1: RED** Write tests in `tests/test_commuting.py`: for `H(0), X(1), H(0)`, legacy returns three gates and `optimizer="commuting"` returns `X(1)` with `commute_disjoint` + `H_inverse` steps, v2 schema, exact replay true. Assert 2-gate removal and the correct changed metric.
- [ ] **Step 2: Run** `python3 -m unittest tests.test_commuting -v`; confirm expected failure because `compile_circuit` rejects the new `optimizer` kwarg.
- [ ] **Step 3: GREEN** Implement the versioned receipt branch and the deterministic commute-then-reduce strategy. Scan increasing `(i,j)` among pairs matching an existing two-gate rule; only accept when intervening support is disjoint from the pair. Prefer existing adjacent reductions first. Emit each bubble swap explicitly; then emit the actual reduction, restarting the search. Reuse the unchanged v1 deterministic verifier branch. In v2 replay, derive expected moves from the same canonical selection policy, check each trace record and full exact operator equality, reject changed endpoint/scope/digest/metrics.
- [ ] **Step 4: Run** `python3 -m unittest tests.test_commuting -v` and `python3 -m unittest tests.test_compiler -v`; both must pass.
- [ ] **Step 5: RED→GREEN boundary cases** Add one new test at a time for all five Review Focus cases owned by Task 1, including old v1 receipt replay; run the targeted test to see it fail if the behavior is missing, implement the minimum fix, then re-run targeted and full Task 1 suites. For a safety property that already passes before a code change, record the pre-existing coverage and add a mutation that proves the test can go red.
- [ ] **Step 6: Commit** `git add physqed_q/compiler.py tests/test_commuting.py` then `git commit -m "feat: add exact commuting optimizer with versioned proof receipts"`.

### Task 2: Expose opt-in strategy through CLI and local dashboard

**Files:**
- Modify: `physqed_q/__main__.py`, `physqed_q/web.py`
- Modify: `physqed_q/web_assets/index.html`, `physqed_q/web_assets/app.js`, `physqed_q/web_assets/styles.css`
- Modify: `tests/test_cli.py`, `tests/test_web.py`, `tests/test_web_ui.mjs`

**Interfaces:**
- Consumes: `compile_circuit(circuit, optimizer="adjacent"|"commuting")` from Task 1.
- Produces: CLI flag `compile --optimizer commuting` (default `adjacent`), web `POST /api/compile` optional `optimizer` string (default `adjacent`), accessible UI selector with both choices. V2 verification works on existing `POST /api/verify` and supported Lean checks remain distinctly labeled.

- [ ] **Step 1: RED** Add CLI test that the new flag emits and verifies a v2 receipt for disjoint interleaving, and explicit default CLI test that still returns v1. Run `python3 -m unittest tests.test_cli -v`; expect argument rejection.
- [ ] **Step 2: GREEN** Add constrained CLI argument choices and forward them to `compile_circuit`, with documentation in the help string; rerun tests.
- [ ] **Step 3: RED** Add real HTTP test for `{"circuit": ..., "optimizer":"commuting"}` returning v2, while no optimizer returns v1; unsupported values and types must be HTTP 400. Run `python3 -m unittest tests.test_web -v`; expect failure.
- [ ] **Step 4: GREEN** Extend only `/api/compile` body validation to optionally allow the recognized optimizer field; preserve strict `receipt`-only shape for other endpoints. Rerun HTTP tests.
- [ ] **Step 5: RED** Add UI behavior test for keyboard-operable optimizer control and the exact JSON API payload choice; run `node tests/test_web_ui.mjs` and observe expected failure.
- [ ] **Step 6: GREEN** Add accessible optimizer `<select>` and send its value in `Optimize & Verify`; keep stale-request protection and truthful receipt/Lean display; rerun Node and JavaScript syntax checks.
- [ ] **Step 7: Commit** stage these eight files and `git commit -m "feat: add opt-in commuting optimization to CLI and dashboard"`.

### Task 3: Reproducible improvement cases, documentation and CI

**Files:**
- Create: `examples/commuting.json`, `benchmarks/commuting_suite.py`, `tests/test_commuting_benchmark.py`
- Modify: `README.md`, `benchmarks/README.md`, `.github/workflows/physqed-q.yml`

**Interfaces:**
- Consumes: Task 1's two optimizer strategies and metric function.
- Produces: `python3 -m benchmarks.commuting_suite` outputting deterministic JSON records for a fixed circuit corpus with v1/v2 gate/depth/T metrics and full exact verification booleans.

- [ ] **Step 1: RED** Add a benchmark test requiring a documented interleaving fixture to improve from 3 gates to 1 with v2 and demanding each emitted receipt replay verifies exactly; run `python3 -m unittest tests.test_commuting_benchmark -v`, observe expected import/file failure.
- [ ] **Step 2: GREEN** Add the fixture, the deterministic self-contained comparison script and a stable JSON report. Include one improvement, one parity and one blocked-overlap case; no runtime superiority claim.
- [ ] **Step 3: Run** benchmark test, `python3 -m benchmarks.commuting_suite` twice for byte-identical JSON, and `python3 -m unittest discover -s tests -v` for the complete repository; record actual outcomes.
- [ ] **Step 4: Document** update the v0.6 README example and benchmark scope; add Node UI test invocation and new benchmark test command in GitHub CI, preserving optional Qiskit isolation.
- [ ] **Step 5: Run** `node --check physqed_q/web_assets/app.js`, `node tests/test_web_ui.mjs`, full Python suite with optional pinned Lean when available, and `git diff --check`. Inspect for stale status/false verification claims.
- [ ] **Step 6: Commit** stage all Task 3 files and `git commit -m "test: add reproducible exact commuting optimization cases"`.

### Task 4: Independent review and release handoff

**Files:** no product code unless review finds a Critical/Important defect; any repair must follow new failing-test → passing-test sequence.

- [ ] **Step 1:** Request a fresh read-only reviewer to inspect the whole branch, including receipt trust boundaries, denial-of-service caps, and old v1 attestation behavior.
- [ ] **Step 2:** Record all findings; fix Critical/Important findings with RED→GREEN tests and rerun all suites. Defer minor polish with a disclosed limitation.
- [ ] **Step 3:** Compare changed files with the approved spec and verify test results. Open an isolated draft PR stacked on the v0.5 branch once remote head safety is checked; do not merge `main`.
- [ ] **Step 4:** State the actual reviewed capabilities, optional dependency skips, and remaining Milestone A finite-search experiment. Do not claim superiority or deploy the public platform.

## Next independently scoped plans

After this release's acceptance, a separate Milestone A2 plan covers bounded
one-qubit exhaustive synthesis with independently verified search completeness.
Milestone B then adds fixed held-out benchmarking against optional Qiskit,
pytket and PyZX plus target graph models; Milestone C adds SDK, API, MCP and
secure hosted demo, with explicit approval for any hosting cost or public-site
change. Their absence from this plan is deliberate, not an abandonment of the
approved three-part programme.
