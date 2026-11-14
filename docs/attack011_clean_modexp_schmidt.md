# PHYSQED-Q — Attack 011

**Research date:** 14 November 2026  
**Author:** Tony Newton, Newton Astro Labs, London, UK  
**Status:** `MODULAR_ARITHMETIC_CORE_VERIFIED__MPS_RESTRICTED_BOUND_PROVED__FULL_SHOR_OPEN__BPP_BQP_OPEN`

## Completed

1. A uniform polynomial-size `H`/`CCZ` compiler for the *clean, coherent modular-exponentiation core* of order finding. The emitted circuit uses only Hadamard and CCZ gates, two fixed `|1>` ancillas, clean compute/copy/uncompute, repeated-squaring factors, fixed-constant arithmetic and no exponential truth-table synthesis.
2. A general exact Schmidt-rank theorem for the coherent modular-exponentiation state: `rank=min(2^m,ord_N(a))` across exponent/output.
3. The explicit family `N=2^s`, `a=5`, `s>=3`, for which `ord_{2^s}(5)=2^{s-2}`, giving an exact **and approximate** MPS lower bound in the specified physical ordering. To achieve squared fidelity at least `1-eps`, bond dimension must satisfy `D>=(1-eps)*2^(s-2)`.
4. Exact Hadamard–Walsh sampling of the power-of-two-order family: `z` is uniform in `[0,2^(s-2))`; in the joint outcome `(z,5^u mod 2^s)`, `z,u` are independent uniform variables in that range.
5. A counterexample against overstatement: the same output distribution is classically sampled in polynomial time from the public description. This is a lower bound on one tensor-state representation, **not** on all classical algorithms.

## Deliberately not completed

- Full uniform Shor-to-HCCZ factoring algorithm. There is **no general inverse cyclic QFT, approximation/synthesis error budget, continued-fraction factoring, or end-to-end success theorem** in this release.
- A classical lower bound outside fixed-cut MPS descriptions.
- An unconditional result for `BPP` versus `BQP`.

## Exact tests

- 7/7 unit tests passed.
- Independent alternative gate interpretation: 276 circuits, 2,070 public basis cases, up to 968 allocated wires.
- Exact sparse quantum-state checks for six power-of-two-order circuits (up to 574 wires, 5,590 H/CCZ gates and Schmidt rank 64), with all scratch qubits clean.
- Independent arithmetic/group-theoretic second verification: 6,830 rank-spectrum cases, 1,390 flat cases and 88 exact 2-adic order tests through s=90.
- Negative control with `N=21, a=2, ord=6`, where the Hadamard-only readout is not the power-of-two uniform law.

### Local commands

```bash
PYTHONPATH=. python -m unittest discover -s tests -p test_modexp_core.py -v
PYTHONPATH=. python tests/independent_attack011_audit.py
PYTHONPATH=. python tests/second_pass_attack011.py
```

## Files

- `physqed_q/modexp_core.py`: compiler and deliberately bounded exact simulator.
- `tests/test_modexp_core.py`: seven end-to-end tests.
- `tests/independent_attack011_audit.py`: alternative Toffoli parsing, direct basis checks and full-character sums.
- `tests/second_pass_attack011.py`: independent modular-order/group-spectrum verification.
- `docs/Attack011_Modexp_HCCZ_Schmidt_Barrier.pdf`: 3-page two-column research note.
- `docs/Attack011_Modexp_HCCZ_Schmidt_Barrier.tex`: editable source.
- `results/independent_audit.json`, `results/second_pass.json`, `results/unit_tests.txt`: audit outcomes.
- `SHA256SUMS.txt`: release hashes.

## Prior art and novelty limits

Reversible modular exponentiation is classical quantum-compilation territory (Shor, standard Qiskit Shor documentation), H+Toffoli universality is due to Shi/Aharonov, and Schmidt-rank/MPS bond lower bounds are standard tensor-network mathematics. The explicit power-of-two family is an **independent implementation and restricted certificate**, not yet a clear mathematical novelty claim. The 2026 literature also emphasizes that extensive entanglement and magic need not imply full classical hardness.

## Next research gate

Implement an **approximate inverse cyclic QFT** in the real H+Toffoli/HCCZ model with a fully explicit polynomial gate synthesis and error budget. Only then combine the arithmetic core with generic modular order recovery and factoring. The structural MPS theorem is an analytic verifier and negative control, not a BPP lower-bound method.