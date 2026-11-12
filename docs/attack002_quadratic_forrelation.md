# PHYSQED-Q — BPP versus BQP, Attack 002

**Tony Newton**  
Newton Astro Labs, London, UK — tony.newton79@gmail.com  
12 November 2026

**Release status:** ATTACK002_QUADRATIC_EXPLICIT_CLASSICAL_SHORTCUT_VERIFIED. The unrestricted BPP versus BQP question is **not** solved. This is a reproducible, standard quadratic Gauss-sum / Clifford classical-simulation certificate; mathematical originality is **not** claimed.

## The tested explicit-input family

For Boolean polynomials p,q:F₂ⁿ→F₂ of degree at most 2, explicitly described by O(n²) algebraic normal form coefficients, put f(x)=(-1)^p(x), g(y)=(-1)^q(y), and

Phi_n(f,g) = 2^(-3n/2) * Σ_{x,y∈F₂ⁿ} (-1)^[p(x)+x·y+q(y)].

Let A_p and A_q be the symmetric zero-diagonal polar matrices of the quadratic terms, and define

    M = [ A_p   I  ]
        [  I   A_q]

over F₂, with k=dim ker(M)=dim ker(I+A_q A_p), an even integer.

**Theorem (standard).** The signed Forrelation is exactly 0 or ±2^((k−n)/2). Its sign, zero/nonzero status and exact squared magnitude are computable deterministically in polynomial time from the explicit ANF coefficients. Therefore every Forrelation promise problem whose inputs explicitly contain just these quadratic coefficients and whose outcome is determined by Phi belongs to P. This particular class cannot witness BPP != BQP.

### Exact constructive proof

Write H(x,y)=p(x)+x·y+q(y). If a quadratic term ab occurs, express H=ab+aL(z)+bR(z)+T(z), with L,R affine and T quadratic in the remaining variables. Summing over the two pivot bits gives the identity

    Σ_{a,b∈F₂} (-1)^(ab+aL+bR+T) = 2*(-1)^(L*R+T).

The product LR is at most quadratic, because Boolean variables satisfy z_i²=z_i. Each elimination removes two variables. At the end the affine sum is either zero (a linear coefficient remains) or exactly ±2^r, yielding the exact integer signed sum. The supplied Python evaluator implements this process using parity sets of squarefree monomials. No exponential truth table is built.

### Independent polar-rank proof

The polar form of H is B(u,v)=H(u+v)+H(u)+H(v)+H(0)=uᵀMv. Let m=2n and R=ker M. Character orthogonality yields

    S² = 2^m Σ_{h∈R} (-1)^(H(h)+H(0))

for S=Σ_z (-1)^H(z). The exponent is linear on R; the final sum is either 0 or 2^k. Hence Phi² is exactly 0 or 2^(k−n). The matrix is alternating, so rank(M), and therefore k, is even. Its block equations imply k=dim ker(I+A_q A_p). This determines magnitudes; the constructive algorithm determines signs.

**Additional standard corollary:** If the quadratic coefficients A_p,A_q are fixed and all 2n linear coefficients are uniformly varied, exactly 2^(2n−k) choices yield nonzero Phi. Thus Pr(Phi!=0)=2^(−k) and E(Phi²)=2^(−n). This follows because restriction of linear forms to the k-dimensional radical is surjective and exactly one restriction cancels H's existing radical restriction.

### Adversarial controls and representation boundary

For even n, Q(z)=Σ_j z_(2j)z_(2j+1) is a self-dual bent quadratic. The explicit phase choices p=q=Q yield Phi=+1; p=Q,q=Q+1 yield Phi=−1. Yet the coefficient-input family is solvable classically in polynomial time. For odd n, k is even and at most n−1, giving |Phi|≤1/√2 in the quadratic subclass.

This **does not** disprove any established black-box Forrelation lower bound: a classical black-box query algorithm does not receive the ANF coefficients, whereas our exact algorithm does. Nor does it show all polynomial-size classical circuit descriptions make Forrelation easy. Girish–Servedio (2025/26) established extremal Forrelation hardness, including conditional hardness results for small-circuit oracles in the *black-box* model, and explicitly distinguish the unproved corresponding white-box claim.

A circuit that measures |0ⁿ⟩ after Hⁿ, phase(f), Hⁿ, phase(g), Hⁿ observes Phi², not Phi's sign. A separate interference construction would be required to distinguish +1 from −1 with that circuit architecture.

## Reproducible verifier and limits

- `physqed_q/quadratic_forrelation.py`: exact polynomial-time quadratic Gauss sum plus separate exponential-size integer Walsh-transform reference.
- `tests/test_quadratic_forrelation.py`: 6 unit tests covering exhaustive 1–2 bit instances, randomized 3–8 bit instances, extremal/zero/negative controls, direct finite Gauss sums and invalid inputs.
- `tests/independent_attack002_audit.py`: separately implemented F₂ Gaussian rank and n=3 exhaustive linear-coefficient fibre census.

**Local audit (12 November 2026):** 6/6 tests passed. Independent verification checked 1,820 rank/Walsh cases and all 4,096 linear-coefficient cases over 64 quadratic-part pairings at n=3. The output is deterministic. GitHub-hosted CI has **not** been confirmed; Python code is not a Lean theorem or hardware demonstration.

From repository root:

```bash
python -m unittest discover -s tests -p 'test_quadratic_forrelation.py' -v
python -m tests.independent_attack002_audit
```

## Next proof target: Attack 003

Explore explicit non-Clifford (for example, cubic-phase) families, retaining a uniform n-dependent generator and a fully specified decision/promise language. Before any lower-bound claim, test explicit classical shortcuts: linear algebra, stabilizer decomposition, tensor-network width, symmetry, hidden-seed leakage and preprocessing of the published generator. An unrelativized separation requires a rigorous lower bound applying to **every** randomized polynomial-time classical algorithm; finite numerical experiments can refute candidate statements but cannot prove this universal exclusion.

## Prior art and references

1. S. Aaronson and A. Ambainis, *Forrelation: A Problem That Optimally Separates Quantum from Classical Computing*, SIAM J. Comput. 47 (2018), arXiv:1411.5729.
2. U. Girish and R. Servedio, *Forrelation Is Extremally Hard*, ITCS 2026, arXiv:2508.02514, doi:10.4230/LIPIcs.ITCS.2026.72.
3. D. Turturean, *A proof of the Aaronson–Ambainis conjecture*, arXiv:2611.09773 (2026).
4. G. Blanc, J. Docter, C. Strassle and L.-Y. Tan, *Proof of the Aaronson–Ambainis Conjecture: An Exposition*, arXiv:2611.11626 (2026).
5. Standard background: quadratic Boolean exponential sums and the Gottesman–Knill classical-simulation principle.

**Verdict:** explicit quadratic-phase Forrelation is efficiently classically computable; BPP != BQP remains open.
