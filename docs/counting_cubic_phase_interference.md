# Counting through cubic-phase interference: exact hardness versus additive easiness

**Tony Newton — Newton Astro Labs, London, UK**

**Technical verification note; not a claim to resolve BPP versus BQP.** The correspondence between H/Z/CZ/CCZ amplitudes, degree-three polynomial gaps and #P-hard strong simulation is established prior art (Montanaro 2017). This branch packages a direct public-input construction, exact verifier and an adversarial classical approximation theorem.

## Uniform 3-CNF → H/CCZ construction

For a signed-literal 3-CNF formula \(\varphi\) with \(n\) inputs, compute its value by a deterministic fan-in-2 gate sequence (NOT/OR/AND), with \(w\) fresh gate outputs \(z_j\). Every gate has a consistency equation \(E_j=z_j\oplus h_j(\text{earlier wires})=0\), where \(h_j\) has degree at most two over \(\mathbb F_2\). The final constraint is \(z_{\rm out}\oplus1=0\).

Introduce Boolean multipliers \(\lambda_1,\ldots,\lambda_{w+1}\) and the degree-at-most-three phase

\[
F_\varphi(x,z,\lambda)
=\bigoplus_{j=1}^{w}\lambda_jE_j(x,z)
\oplus\lambda_{w+1}(z_{\rm out}\oplus1).
\]

There are \(N=n+2w+1\) phase variables. Their algebraic-normal-form monomials, each of degree at most three, compile to CCZ gates with zero, one or two fixed \(|1\rangle\) basis ancillas. Two layers of \(H^{\otimes N}\) sandwich the diagonal phase; the extra ancillas are not Hadamarded.

## All-instance exact identity

For any Boolean constraint bit \(e\),

\[
\sum_{\lambda=0}^{1}(-1)^{\lambda e}=2\,\mathbf1[e=0].
\]

Summing the multiplier bits eliminates every inconsistent computation history; for each satisfying input exactly one assignment of all work outputs survives. Consequently,

\[
\boxed{S_\varphi=2^{w+1}\#\mathrm{SAT}(\varphi).}
\]

The resulting public H–CCZ circuit has all-zero data-register amplitude and probability

\[
\boxed{A_\varphi=\frac{\#\mathrm{SAT}(\varphi)}{2^{n+w}},\qquad
P_\varphi(0)=\left(\frac{\#\mathrm{SAT}(\varphi)}{2^{n+w}}\right)^2.}
\]

This is exact destructive interference, not a computation predicated on a hidden oracle.

**Correct complexity implication.** Exact rational computation of \(P_\varphi(0)\) for these circuits is #P-hard under polynomial-time Turing reductions: multiply the result by \(2^{2(n+w)}\) and take the nonnegative integer square root to recover #SAT. Deciding whether this probability is nonzero is NP-complete. These are hardness classifications, NOT unconditional superpolynomial time bounds and NOT a BPP/BQP separation.

## Second-pass obstruction: a deterministic additive FPTAS

This family is *easy* to approximate to additive accuracy. For every instance \(P_\varphi(0)\le4^{-w}\).

Given rational \(0<\varepsilon\le1\):

1. If \(4^{-w}\le\varepsilon\), output zero and certify additive error at most \(4^{-w}\).
2. Otherwise \(2^w<1/\sqrt\varepsilon\). The final output cone of \(w\) fan-in-2 work gates depends on at most \(w+1\) original input variables. Enumerate only these relevant inputs, calculate the satisfying fraction exactly, and substitute into \(P_\varphi\). At most \(2^{w+1}<2/\sqrt\varepsilon\) assignments are required.

This gives a **deterministic additive approximation algorithm** with bit complexity polynomial in the public formula size and \(1/\varepsilon\), including inverse-polynomial additive precision. It applies only to the specified compiled family; arbitrary H–CCZ circuits are not being claimed easy to simulate.

A unique-satisfying-assignment 3-CNF has \(P_\varphi(0)=2^{-2(n+w)}\). In particular, the public unit-clause family \(\bigwedge_{j=1}^{n}x_j\) has \(w=n-1\) and probability \(2^{-4n+2}\). Thus no uniform positive constant yes/no probability gap follows from this construction.

## Exact local tests

- **12/12** Python unit tests passed, including a distinct sparse integer H–CCZ state simulator.
- Independent audit: **584** ordered two-variable CNFs, including **136** unsatisfiable cases, and **395** direct complete signed-phase sums.
- Six end-to-end sparse H–CCZ circuit checks.
- **220** randomized CNFs over seven rational accuracy thresholds = **1,540** adversarial approximation checks (in the larger local verification bundle); the repository test has a slightly different seeded random subset and six accuracy thresholds.
- 32 unique-SAT asymptotic checks.
- Input, degree, normalization, invalid-probability and precision refusal cases.

Reproduce:

~~~sh
python -m unittest discover -s tests -p test_sat_interference.py -v
python -m tests.independent_attack008_audit
~~~

**Verification boundary:** local exact Python replays are not Lean proofs, hardware experiments, or confirmation of hosted CI. No novelty claim is made for the established #P-hardness connection.

## Sources and next research gate

- Ashley Montanaro, *Quantum circuits and low-degree polynomials over F2*, J. Phys. A 50 (2017), arXiv:1607.08473.
- Michael Bremner, Richard Jozsa and Dan Shepherd, *Classical simulation of commuting quantum computations implies collapse of the polynomial hierarchy*, Proc. R. Soc. A 467 (2011), arXiv:1005.1407.
- Michael Bremner, Ashley Montanaro and Dan Shepherd, *Average-case complexity versus approximate simulation of commuting quantum computations*, Phys. Rev. Lett. 117, 080501 (2016).
- Igor Markov and Yaoyun Shi, *Simulating quantum computation by contracting tensor networks*, SIAM J. Comput. 38 (2008).
- Zhengfeng Ji, Yinchen Liu and Zhe'ou Zhou, *On the Complexity of the Circuit Width Problem*, arXiv:2606.18201 (2026).
- Yasuhiro Kondo, Ryuhei Mori and Ramis Movassagh, *Quantum supremacy and hardness of estimating output probabilities of quantum circuits*, arXiv:2102.01960 (2021).

**Verdict:** exact counting obstruction certified; a constructive additive classical shortcut is certified; unrestricted BPP vs BQP is open. The next target is a uniform **constant-gap** circuit promise whose difficulty survives complete public-input preprocessing and adversarial classical approximation.
