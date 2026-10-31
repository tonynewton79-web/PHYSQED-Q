# PHYSQED-Q v0.5 Visual Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a real local graphical circuit editor and proof-status dashboard on top of PHYSQED-Q's Python engine.

**Architecture:** Add a constrained loopback HTTP adapter to existing exact Python interfaces. Serve a standalone vanilla JS/CSS dashboard as package files; all optimization and validation happen server-side.

**Tech Stack:** Python 3 standard library, HTML/CSS, browser JavaScript, unittest; optional Lean 4.24.0.

**Spec:** `docs/superpowers/specs/2026-10-25-visual-dashboard-design.md`

## Global Constraints

- Preserve the original exact kernel and receipt semantics, including honest Lean/hardware flags.
- Local loopback listener only; reject Host spoofing, origin mismatches, oversize and malformed JSON.
- No framework, cloud, npm or Python package dependency at runtime.
- User-input text must never execute as HTML or JavaScript.
- Avoid changes to main; publish via isolated feature branch and draft PR after verification.

## Review Focus

- Repeated JSON keys/nonfinite values are rejected (test in Task 1).
- A malicious Host or Origin cannot POST despite a loopback listener (Task 1).
- Broken and oversized POST bodies terminate quickly with a clear JSON error (Task 1).
- A tampered receipt cannot get a verified response (Task 1).
- A failed optimization cannot leave a stale green verification indicator (Task 2 UI state test by targeted runtime flow).

---

### Task 1: Real, safe HTTP adapter

**Files:** `physqed_q/web.py`, `tests/test_web.py`.

**Interfaces:** `WorkbenchServer` or `make_server` exposing a real `ThreadingHTTPServer` handler; `main(argv)` CLI. JSON endpoints `/api/compile`, `/api/verify`, `/api/lean`, constrained sample GET routes.

- [ ] Step 1: Write `unittest` integration tests using real `HTTPConnection` calls: optimization example produces 7→2 gates and `verified=true`; `/api/verify` rejects a changed receipt; invalid JSON/duplicate keys/oversized bodies, Host and Origin spoofing all fail; sample reads succeed.
- [ ] Step 2: Run `python3 -m unittest tests.test_web -v`; expected: red, missing web module.
- [ ] Step 3: Implement guarded stdlib HTTP adapter and CLI. Preserve exact `compile_circuit`, `verify_receipt`, `certify_receipt` as the only computation sources.
- [ ] Step 4: Run targeted test; expected: all new tests green.
- [ ] Step 5: Run whole suite; expected: no regression. Commit scoped changes.

### Task 2: Visual editor and verified dashboard

**Files:** `physqed_q/web_assets/index.html`, `physqed_q/web_assets/styles.css`, `physqed_q/web_assets/app.js`, `tests/test_web.py`.

**Interfaces:** Browser uses server routes from Task 1; local `circuit` JSON state, load/edit/reorder/import/export source, render gate diagram, one-click compile/replay, optional Lean report, download receipt.

- [ ] Step 1: Extend integration tests to fetch actual HTML/JS/CSS assets, reject traversal paths, and verify rendered page can be served on ephemeral port; red until assets exist.
- [ ] Step 2: Write responsive accessible markup, style, and JS for all stated user flows, using only textContent for user data and never generating a green success state before API reply.
- [ ] Step 3: Run new server tests and `node --check physqed_q/web_assets/app.js`; expected: green.
- [ ] Step 4: Run whole Python suite; expected: green. Commit scoped changes.

### Task 3: Packaging and release verification

**Files:** `README.md`, `.github/workflows/physqed-q.yml`, `tests/test_web.py` if additional acceptance gaps found.

**Interfaces:** `python3 -m physqed_q.web --port 8765`, README reproduction steps, GitHub CI covering HTTP integration.

- [ ] Step 1: Extend tests for CLI parser and served preset behavior where needed; watch any new test fail first.
- [ ] Step 2: Document runtime, scope, proof trust boundary, expected screenshots/examples, and Windows/macOS/Linux commands. Add web tests to Python CI discovery if not already covered.
- [ ] Step 3: Run full suite, `node --check`, real local HTTP smoke command and source diff review; expected: all checks green.
- [ ] Step 4: Push a new isolated branch from v0.4 and open a draft PR targeting the v0.4 branch; inspect changed-file list and CI status.
