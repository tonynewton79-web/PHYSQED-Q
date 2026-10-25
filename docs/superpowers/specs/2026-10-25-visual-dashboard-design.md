# PHYSQED-Q v0.5 — Local Visual Quantum-Circuit Workbench

Date: 25 October 2026. User direction: build the proposed Python visual
circuit editor, optimization dashboard, and one-click verification next.

## Purpose

Let a researcher show and inspect the actual bounded PHYSQED-Q engine in a
modern graphical interface. The GUI is a real front end to the same exact
Python semantics and receipt replay used by the CLI, not a mock optimizer.

## Product choice and alternatives

- **Selected: local web workbench served by Python's standard library.**
  Works across Windows/macOS/Linux with Python and a normal browser, needs
  no JavaScript build pipeline, and stays connected to the exact engine.
- Tkinter desktop GUI: no browser required, but harder to style, package and
  demonstrate across operating systems.
- Hosted JavaScript site: easy to share a URL, but needs backend hosting and
  additional deployment/security work; a static-only implementation could not
  run the Python/Lean verification engines honestly.

## User flow

1. `python -m physqed_q.web` starts a loopback-only HTTP server and prints
   its URL. Optional `--open` requests the default browser.
2. The screen opens with a real seven-gate optimization example. The user
   changes the circuit name, qubit count (1–4), and gate sequence using a
   palette, source diagram, order controls, and deletion. They can load Bell,
   GHZ, or optimization examples, and import/export source-circuit JSON.
3. `Optimize & Verify` posts the source to `/api/compile`; the server calls
   `compile_circuit` then independently `verify_receipt`. The UI displays
   before/after metrics, circuit diagrams, applied rules, exact operator
   digest and an explicit exact-replay success result, or a visible error.
4. The user can download the complete JSON receipt and request the optional
   Lean proof separately where installed. Lean success is never inferred from
   Python replay, and remains restricted to two-qubit/16-gate receipts.

## Contracts

- No change to `kernel.py`, `compiler.py`, or the meaning of their receipts.
- Public read-only routes: `/`, `/app.js`, `/styles.css`, `/api/examples/<name>`
  where name is exactly `bell`, `ghz`, or `optimize`.
- JSON POST `/api/compile` takes `{ "circuit": <validated-circuit> }` and
  returns `{ "receipt": ..., "verification": ... }` on success.
- JSON POST `/api/verify` takes `{ "receipt": ... }` and returns the exact
  replay verification; `/api/lean` takes `{ "receipt": ... }` and returns a
  Lean v2 attestation only if the pinned toolchain and theorem actually pass.
- All responses include an explicit content type, `Cache-Control: no-store`
  for JSON, and `X-Content-Type-Options: nosniff`.
- Reject invalid JSON (including duplicate fields/nonfinite constants),
  wrong object shape, unexpected endpoints, oversize payloads above 256 KiB,
  disallowed content types, path traversal, cross-origin writes, and Host
  headers not exactly loopback. Bind to `127.0.0.1` only by default.
- The UI uses DOM `textContent` for user-controlled labels and error strings.
  Never use `innerHTML` for untrusted values. All receipt success markers must
  come from server response after actual computation, not UI assumptions.

## Boundaries

This is a local research prototype, not a hosted multi-user service, actual
QPU, quantum speedup, general-purpose compiler, or hardware-specific router.
The general Python path accepts at most four qubits and 64 supported gates;
the optional Lean attestation is two qubits and 16 gates per word. The original
receipt retains `lean_kernel_verified=false`, even when a distinct Lean report
is obtained. A digest is not an authenticity signature.

## Acceptance

Real HTTP integration tests confirm useful successful results, genuine
invalid-input rejection and loopback security, browser assets served from
the repository, actual JSON samples, and a tamper-resistant replay endpoint.
Python suite remains green. JavaScript syntax is checked with Node; a real
browser smoke test should be run where a browser binary is available.
