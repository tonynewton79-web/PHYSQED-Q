# PHYSQED-Q — BPP/BQP Attack 004

**Dense cubic bent-dual circuits, exact perfect-gap quantum signal and a public-dual classical simulation barrier**  
Tony Newton — Newton Astro Labs — 12 November 2026

**Status:** exact restricted theory plus independent finite replay; **not** a proof that BPP != BQP, and no originality claim for Maiorana–McFarland bent functions, Parseval or sampling.

## 1. Explicit cubic family of growing interaction width

Let r>=2, m=2r and n=4r. For a in F_2^r define Q_j(a) as the XOR of a_i*a_k for all 0<=i<k<r when j is even, or when (i+2k+3j) mod 5 <4 for odd j. Put Q=(Q_j) and

    pi(a,b) = (a,b XOR Q(a)),  a,b in F_2^r.

Then pi is a quadratic involution. Write x,y,u,v in F_2^m and t in F_2^n. Set

    p(x,y)=x.pi(y),
    g_t(u,v)=v.pi(u) XOR t.(u,v).

These are *explicit* algebraic-normal-form Boolean polynomials of degree exactly three, with 2r quadratic monomials and C_r cubic monomials per phase, where

    ceil(r/2)*binom(r,2) <= C_r <= r*binom(r,2).

They have polynomial-size uniform CZ/CCZ circuits. For p(c,d,a,b), the cubic terms include d_0*a_i*a_k for all i<k, so its degree-three interaction primal graph contains K_r: treewidth >=r-1=Omega(n). In every variable order at least one cubic monomial has span >=r. Thus the small-width premise of Attack 003's O(n*4^w) transfer algorithm cannot hold. This is **not** a lower bound against other classical methods.

## 2. Exact perfect quantum acceptance

The ordinary unnormalized Walsh transform of the Maiorana–McFarland phase p is

    W_p(u,v)
      = sum_(x,y) (-1)^[x.pi(y) + x.u + y.v]
      = 2^m * (-1)^[v.pi_inverse(u)].

This follows by summing over x: all y except pi(y)=u cancel. Because pi_inverse=pi, g_0(u,v)=v.pi(u) is its publicly computable Boolean dual. With signed Forrelation

    Phi(p,g)=2^(-3n/2)*sum_(z,w) (-1)^[p(z)+z.w+g(w)],

we obtain exactly

    Phi(p,g_t) = 2^(-n)*sum_w (-1)^(t.w)
               = 1 if t=0, and 0 otherwise.

The circuit H^n, phase(p), H^n, phase(g_t), H^n measures all zeros with probability |Phi|^2, therefore **exactly 1 versus 0**, uniformly in n. A global sign flip of g changes Phi to -1 in the yes case but does not change the probability. This is a public instance of established bent-function theory, not a newly proved quantum-class separation.

## 3. Stronger theorem: public bent dual collapses Forrelation to BPP

**Theorem (public-dual sampling).** Suppose p is any efficiently evaluable *bent* Boolean phase on even n bits and its Boolean dual d is publicly computable in polynomial time:

    W_p(y) = 2^(n/2) * (-1)^d(y).

For **any** polynomial-time evaluable Boolean phase g,

    Phi(p,g)= E_(Y uniform in F_2^n) [(-1)^(d(Y)+g(Y))].

Therefore a classical randomized algorithm estimates signed Phi to additive epsilon with failure probability eta using O(epsilon^-2*log(1/eta)) dual/phase evaluations (Hoeffding: failure <=2*exp(-M*epsilon^2/2)). Any such constant-gap explicit-input Forrelation promise belongs to BPP. This even holds when g is a dense high-degree circuit. It does **not** apply when the needed dual cannot itself be computed efficiently.

For the narrower affine-tilt family here, a three-Boolean-query classical oracle test is already sufficient given the public generator: query g_t(0) to cancel an unknown constant offset; query g_t(z1),g_t(z2) for two independent uniform z1,z2. Subtract public g_0 and that offset. If t=0 both discrepancies are zero. If t!=0, t.z1 and t.z2 are independent fair bits, so the test rejects correctly with probability exactly 3/4. It always accepts yes. The explicitly encoded ANF promise is actually in deterministic P: compare with p and the public dual, then read the linear discrepancy.

## 4. Universal random-linear-mask obstruction

**Theorem (Parseval).** For any Boolean phases p,g on n bits, define g_t(y)=g(y)+t.y. Then

    sum_(t in F_2^n) Phi(p,g_t)^2 = 1.

Proof: put h(y)=(-1)^g(y)*W_p(y) and S_t=sum_y (-1)^(t.y) h(y). Orthogonality gives sum_t S_t^2=2^n sum_y W_p(y)^2=2^(3n), and normalization gives the claim. Hence

    Pr_t[ |Phi(p,g_t)| >= delta ] <= 1/(2^n delta^2).

Random independent linear masks almost never create a constant Forrelation gap. For the bent-dual family, exactly one mask has nonzero Phi, saturating the sum identity.

## 5. Source, verification, and next proof obligation

Files:

- \`physqed_q/dense_bent.py\`: polynomial-size uniform cubic ANF constructor, reversible pi, exact in-promise decision certificate, integer Walsh reference, full-mask Parseval check, 3-query randomized tester and public-dual sampling.
- \`tests/test_dense_bent.py\`: 9 unit tests, locally passing, including arbitrary dense cubic second phases, complete n=8 mask orbit, sign/tilt controls, permutation invariance and refusal cases.
- \`tests/independent_attack004_audit.py\`: 304 direct Fourier coefficient comparisons, 750 involution cases, 33 cubic-monomial occurrence checks and complete 256-mask orbit at n=8, locally passing.

Reproduce from root of **the stacked Attack 003 branch** (required for \`cubic_bandwidth.py\`):

\`\`\`bash
python -m unittest discover -s tests -p 'test_dense_bent.py' -v
python -m tests.independent_attack004_audit
\`\`\`

Exact finite checks support the implementation; the separate proofs above establish the all-size statements. No Lean certification, hardware or GitHub-hosted CI claim is made unless independently confirmed.

**Attack 005:** look for a uniformly generated, constant-gap quantum decision problem whose Fourier dual is not explicitly classically sampleable; counterexample-test every public permutation, polynomial, low-rank, tensor-width and stabilizer shortcut. A theorem separating unrestricted BPP and BQP still requires an unconditional lower bound against *all* randomized polynomial-time algorithms. These results emphatically do not supply it.

### Established prior art

1. S. Aaronson and A. Ambainis, *Forrelation: A Problem That Optimally Separates Quantum from Classical Computing*, SIAM J. Comput. 47 (2018), DOI: 10.1137/15M1050902.
2. U. Girish and R. Servedio, *Forrelation Is Extremally Hard*, ITCS 2026, LIPIcs 362, Article 72, DOI: 10.4230/LIPIcs.ITCS.2026.72.
3. Maiorana–McFarland bent functions and Fourier duality are established Boolean-function theory.
4. I. Markov and Y. Shi, *Simulating Quantum Computation by Contracting Tensor Networks*, SIAM J. Comput. 38 (2008), DOI: 10.1137/050644756.

**Terminal status:** PASS_ATTACK004_DENSE_CUBIC_PERFECT_SIGNAL_PUBLIC_DUAL_BPP_COLLAPSE; BPP != BQP remains open.
