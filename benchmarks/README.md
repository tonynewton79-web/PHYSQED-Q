# Reproducible optional Qiskit comparisons

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
