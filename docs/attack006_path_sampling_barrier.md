# Exact Path-Sampling Barriers in Explicit Hadamard–CCZ Forrelation Circuits

**Tony Newton — Newton Astro Labs — 12 November 2026**

**Verification status:** local exact computations passed; theorems are mathematical claims with self-contained proofs below, not Lean-formalized. **Complexity verdict:** a lower bound is proved only for two explicitly limited classical sampling models; the public-input family is in P. This **does not** establish BPP != BQP or a new unrestricted classical complexity lower bound. Standard bent duality and the sign problem are prior art.

## 1. Explicit uniform H–CCZ promise family

Let \(r\ge2\), \(m=2r\), \(n=4r\). Choose the explicit quadratic map \(Q:\mathbb F_2^r\to\mathbb F_2^r\) in `physqed_q/dense_bent.py\), including \(Q_0(a)=\sum_{i<j}a_i a_j\). Put

\[
\pi(a,b)=(a,b\oplus Q(a)), \quad \pi^2=\mathrm{id}.
\]

With \(x,y,u,v\in\mathbb F_2^m\), define

\[
p(x,y)=x\cdot\pi(y), \quad g_0(u,v)=v\cdot\pi(u),\quad
g_t(u,v)=g_0(u,v)\oplus t\cdot(u,v)
\]

for \(t\in\mathbb F_2^n\). These are degree-at-most-three Boolean ANFs, with \(O(r^3)\) monomials. The cubic interaction graph contains \(K_r\) (so treewidth at least \(r-1\)) because \(Q_0\) contains every quadratic pair.

**Theorem A (exact final state).** For \(D_h|z\rangle=(-1)^{h(z)}|z\rangle\), let \(U_t=H^{\otimes n}D_{g_t}H^{\otimes n}D_pH^{\otimes n}\). Then

\[
\boxed{U_t|0^n\rangle=|t\rangle.}
\]

*Proof.* The Walsh transform is
\[
\sum_{x,y}(-1)^{x\cdot\pi(y)+u\cdot x+v\cdot y}
=2^m(-1)^{v\cdot\pi^{-1}(u)}
=2^{n/2}(-1)^{g_0(u,v)}.
\]
The first phase/Hadamard pair generates the \(g_0\) phase; applying \(D_{g_t}\) cancels \(g_0\) and leaves the linear phase \(t\cdot w\), which the final Hadamard layer turns into \(|t\rangle\). The compiled program has three H layers and two CCZ-implemented phase layers. Degree-2 monomials use a CCZ with one fixed basis-\(|1\rangle\) ancilla; degree-1 monomials use two. The basis ancillas remain unchanged. Constant ANF terms are tracked as global phase, not executed as gates.

This gives a **perfect acceptance probability 1 vs 0**, with YES at \(t=0\). **Nevertheless, the explicit coefficients expose \(t\), so the promised decision problem is in deterministic polynomial time.**

## 2. All-proposal importance-weight variance lower bound

The zero-output amplitude has \(M=2^{2n}\) paths:
\[
A_t=\langle0|U_t|0\rangle
=2^{-3n/2}\sum_{x,y\in\mathbb F_2^n}
(-1)^{p(x)+x\cdot y+g_t(y)}.
\]
Every path has equal absolute weight \(2^{-3n/2}\). For any *full-support* sampling distribution \(q\) on complete paths, consider the conventional unbiased one-path estimator
\[
Y=\frac{2^{-3n/2}\,\sigma_t(Z)}{q(Z)},\qquad Z\sim q.
\]
Its second moment is
\[
\mathbb EY^2=2^{-3n}\sum_z q(z)^{-1}
\ge2^{-3n}M^2=\boxed{2^n},
\]
by Cauchy–Schwarz and \(\sum q=1\). Equality holds iff \(q\) is uniform. Thus
\[
\boxed{\operatorname{Var}(Y)\ge2^n-|A_t|^2.}
\]
The IID mean of \(s\) such samples has mean-squared error at least \((2^n-|A_t|^2)/s\). This is a rigorous exponential *method-specific* MSE barrier, even for importance proposals chosen with full knowledge of phase signs. It does **not** rule out analytic summation, control variates, stratification, deterministic contraction or other classical algorithms.

## 3. Stronger sign-only decision lower bound

In a **different, narrower observation model**, the algorithm is given only IID **uniformly sampled path signs** and is not shown path coordinates, input masks or ANF descriptions. Assume equal yes/no priors. Set \(\varepsilon=2^{-n/2}\). The YES sign is \(+1\) with probability \((1+\varepsilon)/2\); the NO sign is \(+1\) with probability \(1/2\). Let P,Q denote these one-bit distributions.

For \(s\) IID observations,
\[
\chi^2(P^{\otimes s}\Vert Q^{\otimes s})
=(1+\varepsilon^2)^s-1.
\]
Since \(\mathrm{TV}\le\tfrac12\sqrt{\chi^2}\) and equal-prior success is \((1+\mathrm{TV})/2\), a success probability at least \(2/3\) requires

\[
\boxed{s\ge\frac{\ln(13/9)}{\ln(1+2^{-n})}
\ge 2^n\ln(13/9).}
\]

At \(n=8\), the **exact minimum** is \(s=191\). For \(m\) samples the total-variation distance is the rational number
\[
\mathrm{TV}_m=\frac1{2\cdot32^m}
\sum_{k=0}^m\binom{m}{k}|17^k15^{m-k}-16^m|.
\]
Independent exact integer calculations show \(\mathrm{TV}_{190}\approx0.3332619601<1/3\) and \(\mathrm{TV}_{191}\approx0.3348153359>1/3\). TV does not decrease when observations are added, establishing minimality. **Crucial model limitation:** this sign-only lower bound is not valid against an algorithm that sees the public circuit or chooses specified path coordinates.

## 4. Reproducibility

- `physqed_q/path_sampling_gate.py`: all-size analytic certificates, CCZ phase compiler, exact proposal moment, and exact sign-only chi-square.
- `tests/test_path_sampling_gate.py`: 7/7 local test methods, including 256 distinct 8-bit masks, 31 additional 12-bit masks, six full H–CCZ output-state checks, importance-distribution controls and refusals.
- `tests/independent_attack006_audit.py`: four complete 8-bit direct double sums, eight 12-bit independent Walsh checks, 33 exact chi-square/TV inequalities, binomial threshold certification and circuit-size checks.

From repository root:
```bash
python -m unittest discover -s tests -p 'test_path_sampling_gate.py' -v
python -m tests.independent_attack006_audit
```

**Locally checked:** 7/7 tests passed, 287 Walsh comparisons, 4 direct path sums, 6 exact final-state tests, and 33 total-variation/chi-square comparisons. This is local execution, not a claim that hosted CI has passed. The LaTeX proof manuscript and a full deterministic results/manifest package are supplied as a separate downloadable artifact.

## 5. Why the result matters—and why it is not BPP != BQP

| Model/claim | Result |
| --- | --- |
| Polynomial-size H/CCZ circuit with constant gap | YES, perfect 1/0 promise |
| Dense cubic hypergraph / growing interaction treewidth | YES |
| Uniform or nonuniform full-support **single-path importance estimator** | Exponential MSE requirement |
| **Sign-only IID uniform-path oracle**, no coordinates/description | \(\Omega(2^n)\) bounded-error sample requirement |
| Fully informed randomized/classical algorithm | Polynomial-time deterministic decoder exists |
| Unrestricted BPP vs BQP | **OPEN, not proved** |

A new candidate must defeat not just a sampling estimator but **every** allowed classical algorithm in a specified model. Known complexity and quantum-query separation theorems (Aaronson–Ambainis) are prior art; none provide an unrelativized BPP/BQP separation here.

## References

1. Aaronson & Ambainis, *Forrelation: A Problem That Optimally Separates Quantum from Classical Computing*, SIAM J. Comput. 47 (2018), doi:10.1137/15M1050902.
2. Markov & Shi, *Simulating Quantum Computation by Contracting Tensor Networks*, SIAM J. Comput. 38 (2008).
3. Rothaus, *On bent functions*, J. Combinatorial Theory A 20 (1976); Maiorana–McFarland is established bent-function prior art.
4. Aharonov, *A Simple Proof that Toffoli and Hadamard are Quantum Universal*, arXiv:quant-ph/0301040 (2003).
5. Turturean, *A proof of the Aaronson–Ambainis conjecture*, arXiv:2611.09773 (2026).
6. Blanc, Docter, Strassle & Tan, *Proof of the Aaronson–Ambainis Conjecture: An Exposition*, arXiv:2611.11626 (2026).

**Release status:** RESTRICTED_PATH_SAMPLING_LOWER_BOUND_CERTIFIED__EXPLICIT_CLASSICAL_SHORTCUT_CONFIRMED__BPP_BQP_OPEN.
