# PHYSQED-Q — Attack 009: Constant-gap signal-processing obstruction

**Tony Newton — Newton Astro Labs — 12 November 2026**

**Status:** RESTRICTED_MARKOV_GROVER_BARRIER_VERIFIED; **BPP != BQP remains open**. The inequalities and gate universality are prior art. This work provides scoped, independently replayed exact verification, not a new complexity-class theorem.

## Source probability

Attack 008 maps public 3-CNF \(\varphi\), with \(n\) Boolean inputs and \(w\) deterministic work gates, to a H–CCZ circuit with \(P_\varphi(0)=(\#\mathrm{SAT}(\varphi)/2^{n+w})^2\). For unique-SAT, \(p_*=2^{-2(n+w)}\). The unit-clause example \(\varphi_n=\bigwedge_{i=1}^n x_i\) has \(w=n-1\).

## Theorem 1 — bounded univariate polynomial postprocessing

Suppose \(G\in\mathbb R[p]\) is a real polynomial of degree \(d\), \(0\le G(p)\le1\) for every \(p\in[0,1]\), and \(G(0)\le1/3\), \(G(p_*)\ge2/3\). The classical Markov inequality applied to \(x\mapsto G((x+1)/2)\) gives \(\|G'\|_{\infty,[0,1]}\le2d^2\). By the mean-value theorem, \(1/3\le G(p_*)-G(0)\le2d^2p_*\). Therefore

\[
\boxed{d\ge1/\sqrt{6p_*}=2^{n+w}/\sqrt6.}
\]

This is only a **scalar univariate, globally bounded polynomial transformation** restriction. It does not rule out a quantum algorithm using the public formula, additional observables or a different computation. It is a standard Markov-based method, not a novelty claim.

## Theorem 2 — standard Grover amplification

For ordinary two-reflection amplitude amplification,
\[
p_k=\sin^2((2k+1)\arcsin\sqrt p)
=\frac{1-T_{2k+1}(1-2p)}2
\le(2k+1)^2p,
\]
because \(|\sin(m\theta)|\le m|\sin\theta|\). To achieve \(p_k\ge2/3\) from \(p_*\), it is necessary that
\[
\boxed{k\ge(\sqrt{2/3}\,2^{n+w}-1)/2.}
\]
This threshold is **necessary, not sufficient**, since the Grover probability oscillates.

| n | w=n−1 | p* | Necessary Grover k | Necessary Markov degree |
|---:|---:|---:|---:|---:|
| 1 | 0 | 1/4 | 1 | 1 |
| 2 | 1 | 1/64 | 3 | 4 |
| 3 | 2 | 1/1024 | 13 | 14 |
| 4 | 3 | 1/16384 | 52 | 53 |
| 5 | 4 | 1/262144 | 209 | 210 |

All integer rounding is checked with exact integer square roots; no floating-point threshold estimates.

## Correct public-input constant-gap benchmark

**HCCZ-CIRCUIT-ACCEPT** takes the full public H/CCZ circuit, input computational-basis state and output wire, with a promise that output-one probability is at least 2/3 or at most 1/3. This is a standard PromiseBQP-complete problem: H and Toffoli are quantum universal, and Toffoli is H–CCZ–H on its target. A randomized polynomial-time classical solver for all promised H/CCZ circuits would imply BQP=BPP. Proving nonexistence remains open.

The package tests a five-qubit non-Clifford **toy control**: H on three data qubits, CCZ, and H on the output gives probability 1/4; a final H–CCZ–H output flip using two fixed basis-|1> ancillas makes 3/4. These trivial public examples verify the circuit semantics but do not prove any hardness.

## Reproducibility

- physqed_q/attack009_gap.py: exact rational Grover/Chebyshev evaluation, threshold certificates, public H/CCZ controls.
- tests/test_attack009_gap.py: **7/7 local test methods passed**, including 400 quadratic bound checks, 110 Grover rounding checks, 144 Markov rounding checks, and the five-qubit circuit test.
- tests/independent_attack009_audit.py: independently verifies 330 odd-sine recurrence cases, 40 Chebyshev coefficient identities and 40 unique-SAT threshold cases.

Run from repository root:

~~~bash
python -m unittest discover -s tests -p 'test_attack009_gap.py' -v
python -m tests.independent_attack009_audit
~~~

The three-page manuscript, LaTeX source and SHA-256 package are attached separately in the conversation. The all-size mathematical statements derive from the proofs, not from finite tests. No Lean proof, hardware demonstration, new bounded-error classical lower bound or BPP-versus-BQP separation is claimed. Hosted GitHub CI must be checked independently.

## Established literature

1. A. A. Markov, classical bounded-polynomial derivative inequality (1889).
2. G. Brassard, P. Høyer, M. Mosca and A. Tapp, *Quantum Amplitude Amplification and Estimation* (2002).
3. R. Beals et al., *Quantum Lower Bounds by Polynomials*, J. ACM 48 (2001), 778–797.
4. D. Aharonov, *A Simple Proof that Toffoli and Hadamard are Quantum Universal*, arXiv:quant-ph/0301040 (2003).
5. J. Watrous, *Quantum Computational Complexity* (2009).
6. S. Aaronson, *Quantum Computing, Postselection, and Probabilistic Polynomial-Time*, Proc. R. Soc. A 461 (2005).

**Next gate:** find a nontrivial full-description, constant-gap H/CCZ family with no known classical shortcut and design a mathematically valid restricted or conditional lower-bound research question. An unconditional unrestricted classical lower bound is not established here.
