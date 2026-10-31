# Reproducible benchmarks

## Internal adjacent-vs-commuting corpus (v0.6A)

This fixed, standard-library-only suite compares the default adjacent policy
(v1 receipts) with the opt-in commuting policy (v2 receipts):

```bash
python3 -m unittest tests.test_commuting_benchmark -v
python3 -m benchmarks.commuting_suite > /tmp/commuting-first.json
python3 -m benchmarks.commuting_suite > /tmp/commuting-second.json
cmp /tmp/commuting-first.json /tmp/commuting-second.json
```

The JSON has sorted field names, fixed case ordering and no timestamps or
timings. It includes each raw input and optimized circuit, receipt schema and
digest, input/output gate/depth/T/two-qubit counts, exact replay status, checked
rewrite count, and signed `v2_minus_v1` metric deltas (negative means fewer).
Recreate any receipt with `compile_circuit(case["input"], optimizer="adjacent")`
or `optimizer="commuting"`, then call `verify_receipt` to replay it. The harness
does that replay separately after every compilation and aborts on failure.

Measured results from the fixed corpus:

| Case / raw gate word | Input gates / depth / T | v1 gates / depth / T | v2 gates / depth / T | v2 − v1 gates / depth / T | Exact replay, v1 / v2 |
|---|---:|---:|---:|---:|---|
| Disjoint inverse: H(0), X(1), H(0) | 3 / 2 / 0 | 3 / 2 / 0 | 1 / 1 / 0 | −2 / −1 / 0 | true / true |
| Adjacent parity: T(0), T(0) | 2 / 2 / 2 | 1 / 1 / 0 | 1 / 1 / 0 | 0 / 0 / 0 | true / true |
| Blocked overlap: H(0), CNOT(0,1), H(0) | 3 / 3 / 0 | 3 / 3 / 0 | 3 / 3 / 0 | 0 / 0 / 0 | true / true |

All cases have two qubits; the disjoint fixture is
[`examples/commuting.json`](../examples/commuting.json). Exact verification
means full operator equality in Q(√2,i), including global phase, not just
agreement on a prepared state. Replay checks intermediate rewrites as well as
the endpoint. Depth is ideal disjoint-qubit scheduling, not device time.

This small selected corpus is a regression and reproducibility check, not a
held-out performance study or a comparison with an external optimizer. It
establishes neither global optimality nor general improvement, physical
fidelity, scalability or quantum advantage. No Lean or Qiskit is invoked.

## Optional Qiskit comparisons (separate dependencies)

The harness runs the same bounded input circuits through PHYSQED-Q v0.1
and Qiskit's `transpile`, recording the actual Qiskit version, basis, seed,
optimization level, and raw resource counts. It requires Qiskit only for the
comparison, not for PHYSQED-Q's compiler or verifier.

```bash
python -m pip install -r benchmarks/requirements-qiskit.txt
python -m benchmarks.qiskit_compare examples/optimize.json --level 3 --seed 2026
python -m unittest discover -s tests -v
```

The fixed native gate alphabet is H, X, Z, S, SDG, T, TDG, CX, CZ, SWAP,
without a physical coupling map or noise model. `depth` is an ideal circuit
layer count, not real-device time. The harness only marks Qiskit outputs
`exact_operator_equivalent` if the output has zero explicit global phase,
contains only representable gates, and PHYSQED-Q independently computes an
identical *full* exact operator. Outputs with nonzero phase are marked
`not_checkable`, even if equivalent up to global phase physically.

## Observations from a single local Qiskit 2.6.1 run

With seed 2026 and optimization level 3, the three example circuits gave:

| Input | PHYSQED-Q gates / depth | Qiskit gates / depth | Full exact operator comparison |
|---|---:|---:|---|
| Bell | 2 / 2 | 2 / 2 | Equivalent |
| GHZ | 3 / 3 | 3 / 3 | Equivalent |
| Seven-gate optimization witness | 2 / 2 | 2 / 2 | Equivalent |

At Qiskit level 1, the seven-gate example yielded 3 gates / depth 3
with a nonzero reported global phase; it is **not** exactly comparable under
the harness's strict phase policy. These small, selected cases do not support
a claim that either compiler is generally superior. They also do not measure
scalability, physical fidelity, or quantum advantage.

For a meaningful external evaluation, next use prespecified held-out circuit
suites, multiple seeds where relevant, confidence intervals, different target
topologies, and an explicit policy for exact vs global-phase equivalence.
