# PHYSQED-Q — BPP vs BQP, Attack 003

**Exact cubic-phase Forrelation: bounded-width transfer certificates, hidden-chain recovery, and a closed recurrence**

**Tony Newton — Newton Astro Labs — 12 November 2026**

**Status:** PASS_ATTACK003_CUBIC_BANDWIDTH_CLASSICAL_SHORTCUT. An independently tested **restricted classical simulation theorem**, not an unrelativized BPP/BQP separation. The techniques are standard tensor-contraction methods; mathematical originality is not asserted.

## Model

For explicitly specified Boolean algebraic-normal-form (ANF) polynomials $p,q:\mathbb F_2^n\to\mathbb F_2$ of degree at most 3, define the exact signed numerator

$$S_n(p,q)=\sum_{x,y\in\mathbb F_2^n}(-1)^{p(x)+x\cdot y+q(y)},\qquad \Phi_n(p,q)=2^{-3n/2}S_n(p,q).$$

The implementation returns the integer $S_n$ and rational $\Phi_n^2=S_n^2/2^{3n}$, with **no floating-point arithmetic**. The associated three-Hadamard-layer circuit directly measures $\Phi_n^2$, not its sign.

## Theorem 1 — bounded-ANF-bandwidth classical computation

Given a common coordinate order for $p$ and $q$, suppose every monomial has span at most $w$, where span is $1+\max(\mathrm{support})-\min(\mathrm{support})$ (constant monomials have span 0). Then $S_n(p,q)$ is computable exactly using at most $4^{w-1}$ integer states and $O(n4^w\,\mathrm{poly}(L))$ arithmetic operations, where $L$ is the explicitly supplied ANF input size and all integers have $O(n)$ bits. Thus an explicitly supplied order of bandwidth $O(\log n)$ suffices for deterministic polynomial-time computation.

**Proof.** Introduce $(x_i,y_i)$ together at step $i$. Multiply by $(-1)^{x_i y_i}$ and by every monomial phase whose largest coordinate index is $i$. All factors required at this step are determined by the new pair and at most $w-1$ previous pairs. Aggregate signed partial sums indexed by those last $w-1$ pairs, of which there are at most $4^{w-1}$. Four transitions per state produce the exact signed sum. An ANF constant is applied as a final global sign. This is a standard one-dimensional tensor-network/transfer contraction. An explicitly provided **simultaneous** permutation of both inputs leaves $x\cdot y$ invariant, and the program checks that the resulting bandwidth meets the stated budget. QED.

This is **not** a universal efficient algorithm for arbitrary cubic ANFs, and does not automatically find a minimum-width ordering.

## Theorem 2 — an infinite cubic chain with a closed recurrence

For $n\ge2$, define $p_n(x)=\sum_{i=1}^{n-2}x_ix_{i+1}x_{i+2}\pmod2$, with the empty sum at $n=2$, and set $S_n=S_n(p_n,p_n)$.

This family has $2(n-2)$ cubic monomial occurrences across $p_n$ and $q_n=p_n$. The minimum variable hitting set of the $n-2$ consecutive-triple supports is exactly $\lfloor n/3\rfloor$: disjoint triples require at least that many vertices, and choosing coordinates $3,6,9,\ldots$ meets all triples. Thus both the cubic-term count and the minimum hitting number grow linearly, but the transfer bandwidth is just $w=3$ and uses 16 states.

Let $s\in\{0,\ldots,15\}$ encode the preceding two pairs as base-four digits and $b\in\{0,1,2,3\}$ the arriving pair. Put $z=4s+b$. The 16-by-16 integer transfer $T$ has contributions

$$T_{z\bmod16,s}\mathrel{+}=(-1)^{[b=3]+[z\mathbin{\&}21=21]+[z\mathbin{\&}42=42]}.$$

With a suitable explicitly defined two-pair initial column $v$, $S_n=\mathbf 1^{\mathsf T}T^{n-2}v$. The following are *exact 16-entry integer row certificates*, directly recomputable without symbolic algebra software:

$$\mathbf1^{\mathsf T}T^4=(16,16,16,16,16,16,16,0,16,16,16,0,16,16,16,0),$$

$$\mathbf1^{\mathsf T}T^6=(80,80,80,80,80,80,80,16,80,80,80,16,80,80,80,16).$$

Consequently $\mathbf1^{\mathsf T}(T^6-4T^4-16I)=0$. Multiplying this identity by $T^{n-2}v$ proves the **all-$n$ exact recurrence**

$$\boxed{S_{n+6}=4S_{n+4}+16S_n \quad (n\ge2).}$$

The initial data are $(S_2,S_3,S_4,S_5,S_6,S_7)=(4,4,16,32,80,160)$.

### Corollary — the unscaled quantum signal vanishes exponentially

The recurrence and positive initial values give $S_n>0$. The six base inequalities $S_n\le(9/4)^n$ for $2\le n\le7$ and the exact inequality

$$(9/4)^6-4(9/4)^4-16=\frac{46001}{4096}>0$$

yield $S_n\le(9/4)^n$ by induction. Therefore

$$\boxed{0<\Phi_n(p_n,p_n)^2\le\left(\frac{81}{128}\right)^n\quad(n\ge2).}$$

Thus the **unscaled** chain is unsuitable for a constant-gap Forrelation promise: the relevant measured signal decays exponentially. Its computational tractability is a separate, stronger white-box obstruction.

## Hidden-order adversarial shortcut

An arbitrary simultaneous permutation may make a cubic chain look nonlocal in its displayed indices. The function \`recover_cubic_chain_order\` checks the 3-uniform supports, builds the edge-overlap graph defined by intersections of size two, and reconstructs a consecutive-triple path when one exists. It validates every resulting triple before accepting, then the Forrelation routine checks the bandwidth of **all** monomials of **both** functions. It is a narrow recognizer, **not** a general efficient bandwidth solver.

## Local verification (12 November 2026)

- \`physqed_q/cubic_bandwidth.py\`: exact bitmask ANFs; signed transfer contraction; coordinate relabeling and cubic-chain order recovery; independent integer Walsh transform.
- \`tests/test_cubic_bandwidth.py\`: 6 unit tests, including exhaustive 1- and 2-bit inputs, random cubic ANFs to 10 bits, 3-to-192-bit chains, random hidden coordinate permutations, and invalid-input refusal.
- \`tests/independent_attack003_audit.py\`: 380 independent **direct double sums** up to seven bits, compared with the transfer algorithm.
- \`tests/audit_chain_recurrence.py\`: exact 16-by-16 transfer identity, recurrence comparisons at 108 input sizes, plus 394 finite exact-rational decay checks. The **proof for all sizes** comes from the 16-column identity and induction, not those finite checks.

Run from repository root:

\`python -m unittest discover -s tests -p 'test_cubic_bandwidth.py' -v\`

\`python -m tests.independent_attack003_audit\`

\`python -m tests.audit_chain_recurrence\`

**Locally replayed:** 6/6 unit tests passed, all 380 direct double sums agreed, recurrence matrix identity passed. GitHub-hosted CI and Lean certification are not asserted until independently verified.

## Research interpretation and next attack

This result **eliminates** a tempting explicit non-Clifford candidate family. Large CCZ count, large cubic hitting number, and apparent nonlocality under a hidden coordinate permutation are not lower-bound certificates. For Attack 004 seek a uniformly generated explicit family with a nonvanishing promise gap and no low-width/low-rank/decomposition shortcut. Even proving large tensor-network width does **not** imply an unrestricted randomized classical lower bound. No proof of $\mathsf{BPP}\ne\mathsf{BQP}$ is claimed.

## Prior art

1. Ashley Montanaro, *Quantum circuits and low-degree polynomials over $\mathbb F_2$* (2017), arXiv:1607.08473. Proposition 13 gives an $O(2^{|H|}\operatorname{poly}(n))$ algorithm for a hitting set of degree-three terms.
2. Igor L. Markov and Yaoyun Shi, *Simulating Quantum Computation by Contracting Tensor Networks*, SIAM J. Comput. 38 (2008), DOI: 10.1137/050644756.
3. Scott Aaronson and Andris Ambainis, *Forrelation: A Problem That Optimally Separates Quantum from Classical Computing*, SIAM J. Comput. 47 (2018), arXiv:1411.5729.
4. David Turturean, *A proof of the Aaronson–Ambainis conjecture*, arXiv:2611.09773 (6 November 2026).
5. Guy Blanc, Jordan Docter, Carmen Strassle and Li-Yang Tan, *Proof of the Aaronson–Ambainis Conjecture: An Exposition*, arXiv:2611.11626 (8 November 2026).
6. Thomas Huffstutler, David Miloschewsky and Supartha Podder, *A short proof of the Aaronson–Ambainis Conjecture via the completion framework*, arXiv:2611.12795 (9 November 2026).

**Status:** Classical shortcut certified; unrestricted $\mathsf{BPP}$ versus $\mathsf{BQP}$ unresolved; independent specialist review and novelty audit remain open.
