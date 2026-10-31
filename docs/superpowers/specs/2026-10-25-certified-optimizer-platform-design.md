# PHYSQED-Q: certified optimizer, performance laboratory, and research platform

**Design date:** 25 October 2026

**Status:** proposed; approval required before implementation

**Repository:** `tonynewton79-web/PHYSQED-Q`
**Starting point:** draft v0.5 review branch, commit `8a934bacc86015ce2dc28b9d72e3d61d9f0f3d1c`

## 1. Intent

Build three connected capabilities in order: (A) a stronger proof-carrying
optimizer, (B) a measured performance compiler and external comparison suite,
and (C) a secure, usable research platform with a Python SDK and a public demo.
Every claimed improvement must have a reproducible test or an explicit
mathematical certificate. The public repository will describe measured facts,
scope, and limitations, with no competitive slogans or unsupported rankings.

This is an engineering programme, not a claim that one bounded tool surpasses
all existing quantum compilers. No new quantum-hardware claim is contemplated.

## 2. Present system and design constraints

PHYSQED-Q v0.5 accepts declarative H/X/Z/S/SDG/T/TDG/CNOT/CZ/SWAP circuits
with 0–4 qubits and at most 64 gates. Its exact evaluator operates in
`Q(sqrt(2), i)` and compares full operators, not equivalence modulo global
phase. Its deterministic Python compiler applies an adjacent local rule
catalogue and produces self-contained receipts rechecked by an independent
verifier. Two-qubit, at-most-16-gate Lean attestations are optional and
separately scoped. The visual Python application runs on IPv4 loopback; it is
not suitable for direct internet exposure.

The current application, source receipts and older receipt verifiers remain
supported. New verification outcomes must never be inferred from a UI success
state, a SHA-256 digest, or an external optimizer's own assertion.

## 3. Approaches and selected sequence

We considered: (1) proof-first optimization, (2) performance-first synthesis
and target-aware compilation, and (3) a platform-first web/API launch.
The first preserves the strongest distinct capability and establishes a safety
boundary before broadening the algorithms. The second produces measurable
resource improvements under fixed experimental conditions. The third makes the
results usable without treating a loopback development server as production.

**Decision:** all three, sequenced A → B → C, with independent acceptance
gates. A successful gate may ship without waiting for later milestones. Each
milestone gets its own implementation plan and separate draft pull request.

## 4. Milestone A — v0.6 certified exact optimizer

### Scope and algorithm

Add a deterministic **disjoint-support commutation pass**. For two operations
`g_i` and `g_j` with identical ordered target/control operands, allow an
existing certified two-gate reduction across intervening gates only when the
intervening gates act entirely on disjoint qubits. Bring the later operation
left by a sequence of explicit adjacent `commute_disjoint` swaps, then apply
the existing certified rule. At every step the checker recomputes and compares
the full exact operators; no floating-point approximate equality is accepted.

The scheduler must make progress by decreasing an explicit objective:
commutation steps are permitted only as part of a pending gate-count-decreasing
reduction. Choose the leftmost eligible pair and a deterministic tie-breaker,
then restart. Do not admit arbitrary commuting loops or gate-count increases.
Keep exact qubit ordering: `CNOT(0,1)` differs from `CNOT(1,0)`.

Introduce a versioned receipt format for the extra trace rule, while keeping
v0.1–v0.5 receipts replayable under their original deterministic semantics.
Reject unknown rule names, ambiguous JSON, noncanonical inputs, truncated
traces, non-progress traces, or claims of global optimality. Use a rigorously
bounded trace limit derived from the 64-gate cap, and preserve fail-closed
status flags.

Add a bounded one-qubit exact synthesis experiment only as a separately marked
experimental mode: exhaustive operator indexing for source windows of length
at most five in the stated seven-gate alphabet, with deterministic
lexicographic cost order `(T-count, total gates, depth, canonical word)`.
An *optimality* claim is allowed only relative to that stated search alphabet
and length horizon, with a verifier that recomputes the complete finite search;
otherwise label the result a heuristic candidate. Do not force this optional
experiment into the ordinary compiler's runtime path.

### Trust boundary and acceptance

- No semantic equality shortcut: each adjacent commuting swap and reduction
  is independently checked against the exact operator engine.
- Backward-compatibility tests replay saved v1 receipts unchanged.
- Tests include counterexamples where overlapping gates do not commute,
  differently ordered CNOTs, adversarial forged receipt steps, empty circuits,
  and 64-gate stress cases; every new behavior is tested RED before GREEN.
- The source and optimized operator fingerprints agree, and both optimizer
  and checker deterministically reject unsupported cases.
- Benchmark on a fixed corpus containing adversarial gate interleavings,
  with explicit cases that improve over adjacent-only v0.5 and cases that do
  not. Never promise lower T-count or better depth for every circuit.
- Keep existing optional Lean scope truthful. A Python-certified commutation
  receipt is not called Lean-certified until the Lean bridge independently
  validates that receipt under its own supported bounds.

## 5. Milestone B — v0.6 performance laboratory

Provide a prespecified, seeded corpus and resource comparison that separates
**exactly verified**, **verified up to global phase**, **outside exact scope**,
and **not verified**. Compare the same input circuits and compatible basis
rules with Qiskit, pytket and PyZX *when those optional packages are available*.
Record package versions, machine details, optimization levels, seeds,
connectivity model, runtime, gate count, two-qubit count, T-count and depth.

Report paired per-circuit differences and aggregate distributions rather than
selected wins. The benchmark must keep training/development circuits separate
from a frozen held-out test set. Runs must be reproducible from a command and
emit JSON/CSV artifacts, never hand-edited summary claims. Dependencies remain
optional, pinned for the published comparison environment.

Performance development can then add verified exact window replacement and a
target graph routing mode with explicit SWAP bookkeeping. Hardware coupling
and timing/error rates must be described as **models**, not measured hardware
benefits. Broader-than-four-qubit experiments require a separate scalable
verification backend or a strictly labeled non-exact mode; never silently
weaken the existing full-operator guarantee.

**Gate:** correctness on the held-out corpus, no false verification flags,
stable repeatable measurements, and published non-wins as well as wins.

## 6. Milestone C — v0.7 Python SDK and hosted research interface

Refactor the verified engine behind typed, documented Python functions and a
versioned JSON API. Extend the visual editor with explicit explanation of
proof status, optimizer choice, reproducible benchmark runs, downloaded
receipts and a guided verification view. An optional MCP adapter may wrap only
the same allowlisted API operations and must not offer arbitrary code, file
path, shell, network, or Lean-source execution.

The current stdlib loopback server remains the private local workbench. A
public deployment requires a separate production gateway with strict request
size and computation budgets, origin/CORS and Host controls, authentication
where needed, rate limits, container isolation, structured logs, a health
endpoint and no filesystem access to user-supplied paths. Browser status must
always display whether verification was Python-exact, Lean-attested, or not
completed. A static GitHub Pages site alone cannot host the Python backend.

**Deployment decision held for later:** hosting provider, billing limits,
domain, public data policy and whether anonymous computation is permitted.
Do not incur hosting charges or change the public default site without Tony's
explicit go-ahead on those details. First demonstrate a reproducible local
production-mode smoke test and deployment recipe.

## 7. Release quality and presentation

For each stage: architecture/spec review; tests-first implementation; unit,
property, differential, security and regression tests appropriate to the
scope; independent reviewer; clean source diff; repeatable CI; a draft pull
request. Do not merge prior stacked branches or modify the canonical `main`
without a separate release decision. A GitHub Action queued state is not a
passing state. The changelog describes what was actually tested.

The user-facing interface should be clean and accessible on desktop and
mobile, with circuit/receipt download and visual proof status. Browser
accessibility, keyboard use, import safety, status-race resistance, and no
untrusted HTML injection are release gates. Manual browser screenshot QA is
required before calling a public UI polished.

## 8. Explicit non-goals and risks

- No general theorem prover for all quantum physics statements.
- No assumption that a finite local rewrite list finds globally optimal
  circuits or that lower gate count implies lower hardware error.
- No claimed speedup, hardware execution, RSA/Shor breakthrough, or physical
  quantum advantage.
- No user-authored Python/Lean execution through the public API.
- Bounded exact matrices scale exponentially in qubit count; expanding that
  limit without another verifier is unsafe.
- Optional Qiskit/pytket/PyZX versions and availability may differ; label
  absent baselines rather than invent scores.

## 9. Planning handoff

The first implementation plan covers **only Milestone A**, including the
versioned receipt, deterministic commutation pass, independent replay and its
benchmark cases. The one-qubit finite-search experiment follows inside the
same research phase but may be split into a separate PR if code review or
runtime budgets demand it. B and C each need their own plan and design review
after A results are measured. This keeps all three committed directions
without pretending the entire programme is one small software change.
