# Exact coherent adjacency oracle and query accounting

PHYSQED-Q now has a **separate, bounded research backend** for the standard adjacency-matrix quantum query oracle:

```text
O_A |u,v,b> = |u,v,b XOR A[u,v]>
```

A graph is a simple undirected graph with 2--8 vertices. A coherent QUERY on
arbitrary superpositions counts **one oracle invocation**, including a zero
answer, invalid/padded vertex label, or diagonal entry. The program exposes
no data-dependent free graph lookup. The verifier sees the graph to compute
the exact state, but this *verification* access is not charged to the tested
algorithm. A particular program may have been chosen with knowledge of the
graph, so **graph-independence is not inferred** from one graph-instance test.

The new backend is not limited by the existing four-qubit ordinary-gate
compiler. It supports 2--3 k-bit vertex registers, 1--3 answer bits,
up to 12 qubits and 128 operations. The free gates are H, X, Z, CNOT,
and CCZ (the CCZ is free in the query-count metric, **not** in gate count).
It is an exact **real** amplitudes fragment of the Q(sqrt(2),i) field
supplied by the shared PHYSQED-Q gate kernel. No measurement, channels,
noise, arbitrary-rotation gate, hardware or unbounded circuit is covered.

The receipt stores the exact final state of an input basis vector,
the normalized graph/program, a query ledger and the query count,
full gate count, SHA-256 integrity digest and explicit non-proof flags.
It is independently replayed by sparse-state accumulation and also
by the existing dense gate kernel. Both paths share the specified
oracle map; they do not constitute independent formal semantics.

## Six-query fixed-triple triangle phase

For a declared triple (u,v,w) and three zero-initialized scratch bits:

```text
QUERY (u,v) -> e_uv
QUERY (v,w) -> e_vw
QUERY (w,u) -> e_wu
CCZ   (e_uv,e_vw,e_wu)
QUERY (w,u) -> e_wu
QUERY (v,w) -> e_vw
QUERY (u,v) -> e_uv
```

The resulting exact transformation is

```text
|u,v,w>|000> -> (-1)^(A_uv A_vw A_wu) |u,v,w>|000>
```

This identity follows analytically by XOR uncomputation. Every operation
here is graph-independent except the six specified QUERY operations.
The executable family benchmark checks all 8 graph inputs at n=3,
and all 64 graph inputs times four vertex triples at n=4: **264**
finite graph/triple instances with exactly six queries each.

**This is NOT quantum triangle finding.** It marks a *given* triple;
there is no coherent search over all triples, no measured success
probability, no nontrivial general query upper bound and no O(n) result.
The simulated adjacency matrix is known only to the verifier, not
accessed by any additional gate in the declarative program.
A signed hash is not provided; SHA-256 is integrity, not authorship.

## Local usage on CPU

From the repository root with Python 3.11+:

```bash
python -m unittest tests.test_adjacency_oracle -v
python -m physqed_q.oracle_cli demo --vertices 3 --output /tmp/triangle.json
python -m physqed_q.oracle_cli verify /tmp/triangle.json
python -m physqed_q.oracle_cli family --vertices 4
python -m physqed_q.oracle_cli certify examples/adjacency_triangle_n3.json --output /tmp/instance.json
python -m physqed_q.oracle_cli verify /tmp/instance.json
```

All of these run without external Python runtime dependencies or GPU
hardware. CI additionally tests two Python versions. Unsupported oracle
or gate descriptions and altered receipts are explicitly refused.

## Prior art and problem distinction

The graph adjacency oracle is standard, and the compute/phase/uncompute
pattern is well known; neither is claimed as a new quantum algorithm.
See F. Le Gall, *Improved Quantum Algorithm for Triangle Finding via
Combinatorial Arguments*, FOCS 2014, DOI 10.1109/FOCS.2014.31.
Recent 2026 results for **triangle listing**, **edge-list** input and
K4 or other fixed subgraph detection are distinct from the unrestricted
adjacency-matrix decision/finding problem. The open gap in the latter
remains between Omega(n) and O(n^(5/4)); no claim here narrows it.

## Implementation boundary

The distinct contributions in this patch are a typed query program
schema, exact execution and a charged query ledger, independent
state accumulation, closed-world refusal gates, and exhaustive small
graph experiments. The formal mathematical identities and oracle
model are established prior art.
