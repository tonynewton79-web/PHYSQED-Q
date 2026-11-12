# Attack 010 — Public RSA hard-core bits as an H–CCZ benchmark

**Tony Newton · Newton Astro Labs · 12 November 2026**

**Release status:** CONDITIONAL_WHITE_BOX_CLASSICAL_BARRIER__PRIOR_ART_REDUCTION__EXACT_TOY_REPLAY. **Unconditional BPP != BQP remains OPEN.** The underlying complexity theorem is established prior art; this is a finite PHYSQED-Q verification and scoped research benchmark.

## Problem and motivation

Earlier attacks proved lower bounds for restricted classical simulators but not arbitrary randomized polynomial-time algorithms receiving the entire public circuit and input. To test this stronger model honestly, we use a standard cryptographic assumption with exactly those classical quantifiers. **The assumption is not proved by this research.**

For a standard efficiently generated RSA key pair of distinct odd primes p,q, let N=pq have k bits, choose e>=2 with gcd(e,(p-1)(q-1))=1, sample x uniformly in the unit group Z_N*, and publish y=x^e mod N. For a public uniformly random k-bit mask r, define

  L_RSA-GL(N,e,y,r) = parity(r AND x),  where x^e = y (mod N).

Every field (N,e,y,r) is public. The private inverse x and factors p,q are **not** given to the classical decision algorithm. Define the function's output to be zero for syntactically invalid RSA tuples, making a total binary decision language.

## Conditional theorem, with exact logical scope

**Theorem (standard Shor + Goldreich–Levin consequence).** Assume RSA is classically one-way for the specified random key and secret distribution: no classical probabilistic polynomial-time inverter succeeds with non-negligible probability. Then

  L_RSA-GL ∈ BQP \ BPP.

**BQP route.** Shor's algorithm factors N in quantum polynomial time with bounded error. Verify distinct prime factors, gcd(e,phi(N))=1 and y in Z_N*. Compute d=e^{-1} mod phi(N), x=y^d mod N, and the public-mask parity. Repetition guarantees a constant yes/no acceptance gap. Known quantum gate-set universality (Aharonov, building on Shi) permits **uniform polynomial-size H–CCZ circuit families**, since Toffoli(control1,control2,target)=H(target) CCZ H(target), with the usual ancillas/real-amplitude simulation. **Important:** this repo DOES NOT synthesize or simulate a full Shor-to-H–CCZ factoring circuit at cryptographic sizes.

**Conditional classical exclusion.** If one BPP algorithm solved the total language with error <=1/3 on each input, it would predict the public-mask inner product on random valid RSA instances with advantage >=1/6 over random guessing. The Goldreich–Levin hard-core theorem would yield a polynomial-time classical inverter with non-negligible success, contradicting the stated RSA assumption. The theorem has no unproved algebraic steps beyond explicitly invoked standard complexity results.

**Critical novelty boundary:** This is not a novel unrelativized separation. Classical RSA one-wayness *already implies* a quantum/classical computational distinction using Shor. The added masked-bit decision language is a concrete public binary benchmark, not new evidence for RSA one-wayness.

## Exact finite Fourier certificate

For every secret k-bit x and mask r, let b_x(r)=<x,r> mod 2. Orthogonality of binary characters gives the all-size identity:

  W_x(z) = sum_r (-1)^(b_x(r)+z.r) = 2^k if z=x, else 0.

If fewer than one quarter of the truth-table bits are adversarially flipped, the correct normalised Fourier peak is >1/2 while every other has absolute magnitude <1/2. The finite reference verifier uses an **exponential-size** Walsh truth table. That is NOT the efficient Goldreich–Levin decoder invoked by the theorem.

The embedded three-qubit H–CCZ control implements a controlled orbit toggle using a basis-|1> ancilla. On orbit eigenstate |->, exact phase kickback makes the control deterministically |1>; on |+>, it makes it |0>. These are **actual exact H–CCZ state simulations**, but **not a compiled Shor/RSA algorithm**.

## Local verification, independent checks and classical shortcut controls

- Local unit suite: **8/8**.
- Independently computed full public-mask arithmetic: **83,968 cases** across seven toy RSA moduli.
- Independent plaintext/ciphertext examples: **424**.
- Independent direct Walsh frequency delta: **74**.
- Adversarial 20-percent sign corruption recovered exactly: **74**.
- Trivial all-zero public-mask controls: **533**.
- Exact three-wire H–CCZ eigenstate controls: probability **1 vs 0**.
- Toy brute force and modular inversion **do** solve small instances. The code *refuses* to call this a scalable method or large-scale RSA hardness test.

Run in the repository root:

~~~sh
python -m unittest discover -s tests -p 'test_rsa_hardcore.py' -v
python -m tests.independent_attack010_audit
~~~

The chat release includes a fully rendered research PDF, editable LaTeX, exact Python verifiers and SHA-256 manifest. Hosted GitHub CI and independent specialist peer review should be checked separately.

## What remains unresolved

| Question | Status |
|---|---|
| Complete public RSA instance | Yes, by construction |
| Constant-gap quantum decision algorithm | Yes, from established factoring and gate-set theorems |
| Classical lower bound against all BPP algorithms | **Only conditional on RSA classical one-wayness** |
| Large-scale Shor/H–CCZ compiler implemented here | **No** |
| Classical RSA hardness established | **No** |
| Unconditional BPP != BQP | **No** |
| Novel complexity separation theorem | **Not claimed** |

**Next gate — Attack 011:** seek a mathematically independent structural lower-bound technique or a weaker, non-cryptographic assumption. Do not elevate toy Fourier spectra, high magic, or small-circuit failures into universal hardness claims.

## Prior art

1. Peter W. Shor, *Polynomial-Time Algorithms for Prime Factorization and Discrete Logarithms on a Quantum Computer*, arXiv:quant-ph/9508027 (1995/1996).
2. Oded Goldreich and Leonid A. Levin, *A hard-core predicate for all one-way functions*, STOC 1989, DOI: 10.1145/73007.73010.
3. Dorit Aharonov, *A Simple Proof that Toffoli and Hadamard are Quantum Universal*, arXiv:quant-ph/0301040 (2003).
4. Werner Alexi, Benny Chor, Oded Goldreich, Claus P. Schnorr, *RSA and Rabin functions: certain parts are as hard as the whole*, SIAM J. Comput. 17 (1988).
5. Mark Adcock and Richard Cleve, *A Quantum Goldreich–Levin Theorem with Cryptographic Applications* (2002).
