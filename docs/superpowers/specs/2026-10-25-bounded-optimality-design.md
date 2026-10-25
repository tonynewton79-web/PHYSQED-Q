# PHYSQED-Q bounded one-qubit optimality — design

**Date:** 25 October 2026
**Status:** Milestone A2, continuation of the approved certified-optimizer programme
**Baseline:** v0.6A, `feature/certified-commutation-20261025`

## Mathematical contract

Let `A = (H, X, Z, S, SDG, T, TDG)` be a fixed, *ordered*,
one-qubit gate alphabet. A word is an ordered sequence in `A`; the empty
word is allowed. Fix a search horizon `h` with `0 <= h <= 5`. For a
one-qubit source circuit `C`, a successful certificate names a word `w`
of length at most `h`, having exactly the same **full** unitary operator
in `Q(sqrt(2), i)` as `C`, and proves:

> For every word `v` over `A` with `|v| <= h` and `U(v)=U(C)`,
> `(|w|, T_count(w), alphabetical_rank_word(w))` is no greater
> lexicographically than the corresponding tuple for `v`.

In particular, no shorter word in the declared alphabet and horizon can
implement the same full operator. The primary objective is **total gate
count**, not T-count: Tony's latest explicit requirement of “shortest”
refines the T-first exploratory objective in the parent design. On a
single qubit, depth equals the total number of gates. The last key is
lexicographic ordering induced by the *declared* alphabet, not by
Unicode gate-name sorting. T and TDG each contribute one to T-count.

The finite search has exactly `N(h) = sum(7**k for k in range(h+1))`
words, including the identity. `N(5)=19,608`. A successful proof is
relative to the seven-gate alphabet, exact global phase, and declared
search horizon. It says nothing about alternative gate libraries,
ancillas, two-qubit circuits, approximate synthesis, gate latencies or
quantum hardware. If the source's exact operator has no representative
within the horizon, the generator must **reject**, not produce a
heuristic result relabeled as a proof.

## Architecture

Three approaches were considered: (1) a table of precomputed
representatives, (2) deterministic exhaustive exact search with a
separately implemented exhaustive verifier, and (3) a Lean formalization
of the search. Choose **(2)** for this bounded release: the independent
verification reruns the whole finite enumeration and recomputes the
unitary of every candidate using the existing exact semantics. A stored
hash of the generator's table would not be independent evidence. A
future Lean checker can consume a richer certificate only after it
actually compiles and its own scope is established.

The two exhaustive search algorithms are independent of one another,
**relative to the common exact arithmetic and gate-semantics kernel**;
this is not an independent physical or Lean verification of that kernel.

Keep the search in a new `physqed_q/optimality.py`, separate from legacy
`compile_circuit` and `verify_receipt`. The certificate uses a distinct
`physqed-q-bounded-optimality-v1` schema and a validated canonical JSON
digest for accidental-corruption detection, explicitly not an author
signature. A strict shape and size validator must run **before** hashing
untrusted receipts. The checker never trusts declared search size,
winner cost, circuit equivalence, or digest as evidence: it recomputes
them. Both generator and verifier enforce `0 <= h <= 5`, a canonical
one-qubit source (up to 64 gates), a single-qubit winner, a fixed alphabet,
and explicit false Lean/hardware/quantum-advantage flags.

Freeze the `search.objective` JSON value to the exact list
`["total_gates", "t_gates", "alphabet_lexicographic"]`. `scope` is a
fixed map containing `"claim": "bounded exact one-qubit gate-count minimum"`,
`"lean_kernel_verified": false`, `"hardware_verified": false`,
`"quantum_advantage_demonstrated": false`, and
`"integrity_not_authenticity": true`. Optimized and input circuit names
are identical. The verifier checks strict built-in JSON-compatible types,
not merely type-coercible values; a forged but fully rederived valid claim
about a *different* input is a valid statement about that other input,
not proof of provenance from the original input.

Expose as separate CLI commands `synthesize` and `verify-optimality`.
Ordinary `compile`, `verify`, loopback HTTP and UI semantics are unchanged
in A2; there is no public hosting change or merge to `main`.

## Acceptance and failure cases

1. `H X H` is exactly `Z`, and an optimality certificate must produce
   a one-gate representative instead of the original three.
2. `H H` and the empty word produce an exact zero-gate identity.
3. A source with an operator not in the horizon returns an explicit
   unsupported-search result, with **no** verified certificate.
4. A forged winner, scope, word count, cost, input circuit or rehashed
   receipt cannot validate without genuine exhaustive recomputation.
5. Horizon zero works only for the exact identity; booleans, floats,
   negative and greater-than-five bounds are rejected.
6. The generator and checker are byte-for-byte deterministic, and the
   full preexisting Python, Node and optional bridge regression suites
   retain their truthful pass/skip reporting.
7. The T-count and alphabet-order tie-breakers are tested on exactly
   equivalent candidates; even a zero-gate winner with horizon five
   requires all 19,608 words to be accounted for before success.

Ship only through a reviewed isolated draft PR stacked on v0.6A, with
reproducible CLI evidence and an explicit test count. The public README
will use mathematically bounded phrasing without competitor rankings.
