# PHYSQED-Q — Low Factor-Rank Cubic Forrelation and the Universal H–CCZ Target

**Tony Newton — Newton Astro Labs** · 12 November 2026

**Research status:** Exact restricted simulation and bounded compilation tests passed locally. The unrestricted statement **BPP != BQP remains unproved**. These algebraic methods are based on established quadratic Gauss-sum/Fourier splitting; novelty and priority are not claimed.

## 1. A low algebraic-factor-rank theorem

In the Boolean ring `F2[x_1,...,x_n]/(x_i^2-x_i)`, let

```text
p(x) = Q_0(x) + sum_(j=1)^r_p ell_j(x) Q_j(x),
q(y) = R_0(y) + sum_(j=1)^r_q m_j(y) R_j(y),
```

with quadratic-or-lower Q/R and homogeneous linear ell/m. The factor decompositions are **supplied** explicitly, rather than assumed findable from arbitrary degree-three ANFs. Define

```text
S(p,q) = sum_(x,y in F2^n) (-1)^(p(x)+x.y+q(y)),
Phi(p,q) = 2^(-3n/2) S(p,q).
```

**Theorem (standard-method consequence).** With r=r_p+r_q, the exact signed integer S is computable using at most **4^r quadratic Boolean Gauss sums** on 2n variables, in bit complexity 4^r poly(n,L), where L is the explicit input size. Thus, if r=O(log n), the promised explicitly factored family is in deterministic polynomial time.

**Proof.** For Boolean bits s,t,

```text
(-1)^(s*t) = (1/2) sum_(a,b in F2) (-1)^(a*b + b*s + a*t).
```

Apply to each ell_j Q_j and m_j R_j. Enumerate the 2r selector bits, leaving a quadratic phase for each of 4^r branches and an overall factor 2^(-r). Quadratic Gauss sums are exactly computable: when uv+uL(z)+vM(z)+T(z) appears, summing u,v gives 2(-1)^(L(z)M(z)+T(z)), still quadratic; after eliminating quadratic pairs the remaining linear/constant sum is 0 or a signed power of 2. Integer arithmetic is exact and of polynomial bit length. QED.

The supplied decomposition may contain many cubic ANF terms: it is not an algorithm to factor every cubic polynomial, and it does not resolve a universal classical-complexity lower bound.

## 2. Dense cubic hypergraph with rank-one factorization

For the elementary symmetric Boolean polynomials e_i, the identity

```text
e_3(x) = e_1(x)*e_2(x) mod 2
```

holds exactly, since repeated-index pair contributions cancel and each distinct triple occurs three times, leaving parity one. The explicitly expanded e3 has C(n,3) cubic monomials; every pair of variables appears together in a triple, so its primal graph is K_n (treewidth n-1). The minimum variable hitting set for all triples has size n-2. But the displayed product has exactly one linear-quadratic factor. Therefore the pair p=q=e3 admits an **exact 16-branch classical Forrelation algorithm for all n**.

For n=72: **59,640 cubic monomials per phase; hitting number 70; treewidth 71; only 16 quadratic sums.** An invertible binary linear change of coordinates can scramble the visible permutation symmetry while keeping the *supplied* factorization of size one. This defeats purported lower-bound arguments based only on monomial count, interaction treewidth or hitting-set size. This family has **not** been shown to have a nonvanishing Forrelation promise gap; no quantum advantage is claimed.

## 3. Correct fully universal complexity target

The exact three-qubit identity, as complete operators, is

```text
Toffoli_(a,b->t) = H_t CCZ_(a,b,t) H_t.
```

Shi (2002/2003) and Aharonov (2003) proved that Hadamard and Toffoli are quantum universal. Using the standard polynomial-overhead real simulation, the promised **H–CCZ circuit-acceptance** task (given an explicit polynomial-size circuit and 2/3-vs-1/3 acceptance promise) is **PromiseBQP-complete**. This is established prior art, not a new BQP-hardness claim. A polynomial-time randomized classical algorithm solving **all** its promised instances would imply BPP=BQP; no opposite unconditional lower bound follows from our calculations.

The new module `physqed_q/hccz_circuit.py` implements an exact bounded reference (1–12 qubits). For h Hadamards it represents amplitudes as integer numerators over 2^(h/2), verifies the full norm exactly and outputs the measurement probability as a rational Fraction. It checks direct Toffoli permutation against the H–CCZ–H compiled circuit. No hardware, Lean or efficient large-state simulation is claimed.

## 4. Reproduce the exact audit

```bash
python -m unittest discover -s tests -p test_cubic_slice.py -v
python -m unittest discover -s tests -p test_hccz_circuit.py -v
python -m tests.independent_attack005_audit
```

**Locally completed:** 11/11 unit tests; 710 factorized phase pairs compared with an independent Walsh transform; 420 quadratic Gauss sums compared with direct sums; 215 independent Forrelation double sums; 30,600 scrambled-coordinate ANF input checks; 325 random Toffoli/compiled circuit equivalence tests, plus 300 separate circuit sanity tests and all eight Toffoli basis states. GitHub CI and Lean attestation must be checked independently.

**Interpretation:** This research extends the classical-shortcut gates from quadratic phases, bounded-width cubic phases, and publicly computable bent duals to supplied low linear-quadratic factor rank. It does **not** solve BPP versus BQP.

## 5. Next decisive proof target

Attack 006 should identify a uniform subfamily of unrestricted H–CCZ circuits with a genuine 2/3-vs-1/3 or stronger constant promise gap, and subject it to exact algebraic factor rank, tensor-network, stabilizer, symmetry, and classical sampling audits. A restricted lower bound may be worth proving, but must not be misrepresented as a lower bound against all probabilistic polynomial algorithms. The latter would be required for BPP != BQP.

## Prior art

- A. Montanaro, *Quantum circuits and low-degree polynomials over F2*, J. Phys. A 50 (2017), arXiv:1607.08473 (cubic gap and hitting-set simulation).
- Y. Shi, *Both Toffoli and Controlled-NOT need little help to do universal quantum computation*, Quantum Information & Computation 3 (2003), arXiv:quant-ph/0205115.
- D. Aharonov, *A Simple Proof that Toffoli and Hadamard are Quantum Universal*, arXiv:quant-ph/0301040.
- S. Aaronson & A. Ambainis, *Forrelation: A Problem That Optimally Separates Quantum from Classical Computing*, SIAM J. Comput. 47 (2018), arXiv:1411.5729.
- D. Turturean, *A proof of the Aaronson–Ambainis conjecture*, arXiv:2611.09773, 6 Nov 2026.
- G. Blanc, J. Docter, C. Strassle & L.-Y. Tan, *Proof of the Aaronson–Ambainis Conjecture: An Exposition*, arXiv:2611.11626, 8 Nov 2026.
- T. Huffstutler, D. Miloschewsky & S. Podder, *A short proof of the Aaronson–Ambainis Conjecture via the completion framework*, arXiv:2611.12795, 9 Nov 2026.
