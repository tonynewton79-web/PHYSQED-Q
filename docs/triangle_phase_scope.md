# Three-edge triangle predicate: exact, finite verification

This is a scope benchmark prompted by a question about the possibility
of an O(n)-query quantum algorithm for triangle finding.

The circuit in `tests/test_triangle_phase_scope.py` applies the 3-bit
diagonal phase `(-1)^(x*y*z)` to an already-loaded edge-bit register
`|x,y,z>`.  It uses 7 T/TDG and 10 CNOT gates (17 gates in total),
and checks every element of the exact 8-by-8 unitary against CCZ.
The exact full-operator receipt is replayed by `physqed_q.compiler`.

**Not a quantum graph query algorithm.**  No oracle `O_A|u,v,z> =
|u,v,z XOR A_uv>` for unknown adjacency matrix `A` is implemented.
There is no O(n)-query result, no claim of optimality, no general n
complexity result, and no polynomial equations extracted from prose.

Run locally after cloning:

```bash
python -m unittest tests.test_triangle_phase_scope -v
```

The companion PHYSQED test on the physics repository checks the
classical Boolean triangle-existence formula exhaustively for all
unlabeled input bit patterns on labeled n-vertex graphs for n=3,4,5,6,
plus an exact three-variable phase-polynomial identity and a deliberate
wrong-identity rejection.

For prior art on general triangle finding, see Francois Le Gall,
*Improved Quantum Algorithm for Triangle Finding via Combinatorial
Arguments*, FOCS 2014, DOI 10.1109/FOCS.2014.31.

Both tests are existing finite mathematics; a successful run does not
settle the asymptotic quantum-query problem.
