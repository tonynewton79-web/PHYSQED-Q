# Coherent triangle-search experiments, exact probabilities and charged queries

Research-only PHYSQED-Q module: `physqed_q/triangle_search.py`.

## What is verified

For a finite, simple undirected `n`-vertex graph, enumerate **all ordered**
triples `(u,v,w) in {0,...,n-1}^3`, including repeats. Set `N=n^3`.
The uniform query-algorithm input is

`|s> = N^(-1/2) sum_(u,v,w) |u,v,w>`.

Define `f_A(u,v,w)=A_uv A_vw A_wu` with `A_uu=0`.
The coherent marked phase is `P_A|u,v,w>=(-1)^f_A(u,v,w)|u,v,w>`.
Each `P_A` is implemented in the existing adjacency query model by
compute (three `QUERY`), CCZ, and uncompute (three `QUERY`):
**six charged graph-adjacency queries**. The six-call source program is
obtained from `adjacency_oracle.triangle_phase_program(n)` and validated.
All triples in superposition share these six oracle invocations; the
simulator does **not** charge one query per classical basis state.

The graph-independent ideal diffuser is `D = 2|s><s| - I`.
One search iteration is `D P_A`, and the entire program makes exactly
`6*r` coherent oracle calls after `r` iterations. If the user requests
post-measurement candidate verification, three additional adjacency
queries are charged **on every measurement branch**, giving `6*r+3`
for the complete search-and-check procedure.

### Exact mathematical implementation

The state is stored as a rational vector `a_x` representing
`a_x/sqrt(N)`; coherent phase and diffusion are exact rational
transformations. The measured success probability is

`p_success = (1/N) sum_{f_A(x)=1} a_x^2`.

Each state step checks `sum_x a_x^2=N`. A separate *two-amplitude*
derivation checks every final amplitude and the success probability
using the marked fraction `p = m/N`:

`a_mark'=2(-p a_mark+(1-p)a_unmark)+a_mark`
`a_unmark'=2(-p a_mark+(1-p)a_unmark)-a_unmark`.

The two methods share the mathematical problem definition, but calculate
the updates through distinct state representations. This is finite
arithmetic checking, not a Lean theorem about the entire Python source.

With exactly one triangle at `n=3`, `m=6` ordered marked triples,
`p=2/9`, and one Grover iteration gives `722/729` success probability,
with six charged oracle calls. On `K4`, there are four triangles
(`m=24`), and one iteration gives success probability `27/32`.
These fractions and exact failure probabilities are unit-tested.

A successful receipt stores the full per-invocation query ledger, counts,
per-iteration probabilities, the complete **per-ordered-triple measurement
probability distribution**, and the exact total success/failure probabilities,
the two-amplitude result and SHA-256 integrity. `verify_search` does not
trust the checksum; it recomputes the full finite state and all fields.
Falsified probabilities, counts, ledgers and even recomputed forged digests
are refused.

## Crucial scope restrictions

- Input is a **graph-known verification instance**; the algorithm's
  operations are graph-independent, but knowledge of an input graph by
  whoever *chooses* the program is not automatically excluded.
- This is an **ideal query-model** simulator: uniform preparation,
  diffusion and measurement are explicitly abstract graph-independent
  operations. The diffuser is NOT compiled to the 4-qubit gate compiler.
- Rational numbers record **measurement probabilities**, but hardware
  experiments or actual random samples are not performed. For general
  `n`, the state amplitudes may need `1/sqrt(n^3)` outside the original
  exact `Q(sqrt(2),i)` gate kernel.
- Finite budget: `3<=n<=8`, `0<=r<=12`. Full `n^3` triple space.
- Exhaustive family regression: every simple labeled graph for `n=3,4`,
  each checked against exact state evolution and two-amplitude formula.
- For triangle detection, straightforward amplitude amplification has
  about `O(sqrt(n^3/t))` marking iterations if `t` marked triples are
  present. With one triangle, that is `O(n^(3/2))` queries, not `O(n)`.
  No new algorithmic asymptotic upper bound is claimed.
- No new lower bound, optimality theorem, gate synthesis or hardware
  realization follows from a finite successful test.

## Reproduce locally (CPU, Python standard library)

```bash
python -m unittest tests.test_triangle_search tests.test_adjacency_oracle -v
python -m physqed_q.search_cli demo --vertices 3 --iterations 1 --verify-candidate --output /tmp/search.json
python -m physqed_q.search_cli verify /tmp/search.json
python -m physqed_q.search_cli family --vertices 4 --iterations 1
```

The companion [exact adjacency query specification](adjacency_oracle.md)
defines the original bit-flip oracle. The finite compiler remains a
separate, narrower supported gate family. The purpose here is to
differentiate *verified query counting on a specified finite algorithm*
from *solving the unrestricted quantum triangle-finding problem*.
