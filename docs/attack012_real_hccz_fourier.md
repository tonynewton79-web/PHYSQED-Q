# Attack 012 — Rotation-free Fourier measurement in real H–CCZ circuits

**Tony Newton — Newton Astro Labs, United Kingdom — 14 November 2026**

**Verified claim:** A *uniform, polynomial-size, exact H/CCZ implementation* of a **Kitaev-style measured Fourier-stage replacement** for arbitrary multiplicative order, with a proved phase-decoding confidence budget. **Not a gate-by-gate coherent inverse-QFT compiler.** All factoring and phase-estimation methods are established prior art adapted to PHYSQED-Q; no unconditional classical complexity lower bound or new factoring theorem is claimed.

## 1. Exact coherent inverse QFT is obstructed

Every finite H/CCZ circuit with h Hadamards has its computational-basis matrix entries in \(2^{-h/2}\mathbb Z\); clean basis ancillas preserve this property on the effective submatrix. The standard realification of the \(2^m\)-point inverse QFT for \(m\ge3\) has entries \(2^{-m/2}\) and \(2^{-(m+1)/2}\), whose ratio \(1/\sqrt2\) is irrational. A common-denominator H/CCZ matrix has rational ratios for any two nonzero entries. Thus **exact** clean-basis realification is impossible; approximation or a different Fourier procedure is required. This ring-method observation uses established exact synthesis prior art (Amy–Glaudell–Li–Ross, 2023).

## 2. Uniform physical H/CCZ measurement-stage compiler

For public \(N\ge3\), \(1<a<N\), \(\gcd(a,N)=1\), phase bits \(m\), and \(t\) repetitions, allocate \(C=2mt\) control qubits. In each frequency block \(j\), \(t\) controls are measured in X and \(t\) in Y. Their public modular multiplier is \(a^{2^j}\bmod N\).

Re-use the clean reversible modular exponentiation DAG from Attack 011 (basis-one ancillas, XOR/AND Boolean network, compute-copy-uncompute). A joint H layer prepares

\[
|\Psi\rangle=2^{-C/2}\sum_b|b\rangle
\,|a^{\sum_i b_i2^{j(i)}}\bmod N\rangle
\]

with all work wires exactly reset. The circuit size is \(O(C\,s^3)\) gates and wires for \(s=\mathrm{bitlength}(N)\).

For the Y quadrature, *realify* all complex amplitudes using one globally shared rebit \(R\): \(u+iv\mapsto u|0\rangle_R+v|1\rangle_R\). A controlled \(S^\dagger\) on test control \(c\) is **exactly** implemented by CNOT(c,R), then CZ(c,R), since this is the conditional \(ZX\) representing multiplication by \(-i\). The CNOT is \(H_R\,CCZ(c,R,1)\,H_R\); the CZ is \(CCZ(c,R,1)\) using a fixed basis-one ancilla. Complete each control with H and a Z measurement. **Every emitted physical gate is H or CCZ; there are no uncompiled phase rotations.**

## 3. Proven spectral mixture and decoder

Let \(r=\operatorname{ord}_N(a)\). The orbit of 1 under modular multiplication is a cycle of length r. Spectral decomposition gives a latent \(\ell\) uniform in \(\{0,\dots,r-1\}\), *shared by the entire circuit run*. Conditional on \(\ell\), every X/Y test is independent with

\[
P(X_j=0|\ell)=\tfrac12(1+\cos(2\pi2^j\ell/r)),\quad
P(Y_j=0|\ell)=\tfrac12(1+\sin(2\pi2^j\ell/r)).
\]

This does **not** justify pooling independent new targets as though they had the same hidden eigenphase.

For the \(\pm1\) empirical quadrature means \(\hat c_j,\hat s_j\), Hoeffding gives probability at most \(2e^{-t/128}\) for an error exceeding \(1/8\) in either one. A union bound over \(2m\) estimates gives \(4m e^{-t/128}\). Choosing the exact-integer budget

\[
\boxed{t=128\lceil\log_2(4m/\delta)\rceil}
\]

makes the total failure probability no more than \(\delta\).

On the good event, the error vector has norm at most \(\sqrt2/8\); the angular perturbation is less than 0.212 radians. The code uses a **certified 64-direction integer lookup table** computed from rational Machin \(\pi\) bounds and alternating Taylor series, with directional coordinate error strictly below \(2^{-22}\). Quantization adds no more than \(\pi/64+0.01\) radians. Every measured phase is consequently within \(1/16\) of a turn of the true \(2^j\ell/r\bmod1\).

Backward unwrapping selects the correct half at each frequency and produces an *exact rational* phase \(\hat\theta\) satisfying

\[
\boxed{\|\hat\theta-\ell/r\|_{\mathbb T}
<1/(16\,2^{m-1}).}
\]

Set \(m=2\,\mathrm{bitlength}(N)+2\). This is less than \(1/(2N^2)\), so exact rational continued fractions uniquely recover denominator \(r\) whenever \(\gcd(\ell,r)=1\), followed by a public check \(a^r\bmod N=1\). Thus per-run order recovery is at least

\[
\boxed{(1-\delta)\,\varphi(r)/r.}
\]

For suitable even orders, the standard gcd(\(a^{r/2}\pm1,N\)) computation recovers factors. **This is the established Kitaev/Shor method implemented with the real H/CCZ gate alphabet.** It does not imply a new factoring theorem.

## 4. Separate abstract coherent inverse-QFT plan — not implemented in native gates

The software also emits an abstract inverse-QFT circuit (SWAP/H/controlled phases). Omitting controlled rotations beyond dyadic distance \(K\), and demanding per-retained-gate norm error \(\eta\), gives the **conditional** operator norm budget

\[
\|\widetilde F^{-1}-F^{-1}\|_{\rm op}
\le m\pi\,2^{-K}+M\eta.
\]

Choose \(K\) using the rational bound \(m(22/7)2^{-K}\le\varepsilon/2\), and \(\eta=\varepsilon/[2\max(1,M)]\). The abstract matrix verifier passes through six qubits. **No real H/CCZ controlled-rotation synthesizer is provided.** This is a correct error specification, not a completed native coherent inverse-QFT compiler.

## 5. Independent exact checks

- **10/10** local unit tests passed.
- **Nine** full compiled H/CCZ measurement distributions, **22,464 native gates** total, every temporary work wire confirmed clean.
- **1,404/1,404** exact output probabilities matched a completely independent **Gaussian-integer path sum** that never used the spectral-mixture formula.
- Actual native H/CCZ end-to-end circuit for \(N=15,a=2,m=5,t=1\): **3,838 H/CCZ gates**, all 1,024 control outcomes checked independently, exact factor-\((3,5)\) probability **1/2** after public rational decoding.
- **450** separately seeded *analytic-mixture reference trials* for 15, 21, 35 recovered correct orders and factors 70, 49, 49 times, respectively; all 168 coprime-hidden-phase cases decoded correctly. These 450 trials are **not** full native gate-level simulations and use the hidden phase solely for test generation/analysis.
- The 64-root table and statistical budget are exact rational/integer calculations, not numerical curve fits.

Reproduce from the repository root:

~~~sh
python -m unittest discover -s tests -p 'test_fourier_stage.py' -v
python -m tests.independent_attack012_audit
~~~

The full polished 3-page manuscript, editable TeX, manifest and exact verifier outputs are supplied in the separate conversation download bundle. The proof is conditional only on ordinary ideal quantum gates and the stated confidence event; hardware noise, cryptographic-security claims and unconditional BPP/BQP lower bounds are excluded.

## Prior art

1. P. W. Shor, *Polynomial-Time Algorithms for Prime Factorization and Discrete Logarithms on a Quantum Computer*, SIAM J. Comput. 26 (1997).
2. A. Yu. Kitaev, *Quantum Measurements and the Abelian Stabilizer Problem*, 1996.
3. R. B. Griffiths and C.-S. Niu, *Semiclassical Fourier Transform for Quantum Computation*, Phys. Rev. Lett. 76 (1996).
4. R. Cleve, A. Ekert, C. Macchiavello and M. Mosca, *Quantum Algorithms Revisited*, Proc. R. Soc. A 454 (1998).
5. M. Amy, A. N. Glaudell, S. M. Li and N. J. Ross, *Improved Synthesis of Toffoli-Hadamard Circuits*, arXiv:2305.11305 (2023).

**Next frontier:** a genuine efficient approximate *coherent* IQFT-to-H/CCZ rotation compiler with verified clean ancillas and operator-norm budgets; separately, unrestricted structural classical lower bounds remain open.
