# An Exact Public-Input Modular-Counting Benchmark for Hadamard–CCZ Circuits

**Tony Newton** — Newton Astro Labs*, London, UK — tony.newton79@gmail.com  
12 November 2026

*Newton Astro Labs is the trading name under which Tony Newton conducts independent computational research in the United Kingdom; it is not a limited company.*

**Status:** Public-input perfect-gap construction verified; sharp deterministic width-three ordered-read-once branching-program bound proved; Razborov–Smolensky AC^0[2] lower bound applied as established prior art. **The language belongs to P. BPP != BQP is NOT proved. Mathematical novelty is NOT claimed.**

## Uniform public circuit

For each n >= 1 let x be an n-bit *public* basis-state input. Add work qubits a,b initially |00> and ancillas c,d fixed |11>. These yield n+4 wires. Our gate generator produces one **fixed** circuit U_n independent of x, containing only H and CCZ. We use the exact identities on the fixed ancillas

    X_t = H_t CCZ_(t,c,d) H_t
    Toffoli_(u,v -> t) = H_t CCZ_(u,v,t) H_t.

Apply X_a. For each i, apply Toffoli_(x_i,a -> b) and then Toffoli_(x_i,b -> a). Apply X_b, measure b and accept iff b=1. The implementation contains exactly 6n+6 gates, comprising 4n+4 H and 2n+2 CCZ, and is constructible in polynomial time.

**Theorem 1 (perfect gap).** The acceptance probability is exactly 1 if sum_i x_i is divisible by 3 and 0 otherwise.

**Proof.** For x_i=0, the work state stays fixed. For x_i=1, the two controlled Toffolis induce (a,b) -> (b,a XOR b). After the first X_a, the work state is (1,0). The nonzero input bits advance the 3-cycle (1,0) -> (0,1) -> (1,1) -> (1,0). Hence b=0 if and only if the input's Hamming weight is 0 mod 3; final X_b converts this to the stated acceptance. The gate identities are exact on the fixed ancilla subspace, so the output is a computational-basis state, not an approximate quantum distribution. QED.

## Classical white-box lower bounds

**Theorem 2 (sharp deterministic ordered read-once branching-program width).** For n >= 4, every deterministic ordered read-once binary branching program that computes the above language needs width >= 3. Width 3 is sufficient.

**Proof.** At any cut after k bits with 2 <= k <= n-2, prefixes containing 0,1,2 ones induce three distinct residual functions on the remaining input. Suffixes containing 0,1,2 ones distinguish the residuals; the corresponding 3x3 truth-table rows are (1,0,0), (0,0,1), (0,1,0). Distinct residuals cannot reach the same branching-program state. A standard three-state remainder counter attains the bound. QED.

**Theorem 3 (established Razborov–Smolensky prior art).** The function MOD3 is not in nonuniform polynomial-size constant-depth AC^0[2], whose gates include AND, OR, NOT, and parity. Therefore the public-input acceptance function of U_n is not in this restricted classical class, **even when the classical circuit designer knows and hardwires the entire fixed U_n description**. This invokes the known theorem, not a new lower-bound proof.

**Theorem 4 (public-description query ceiling).** For an O(n)-gate explicit public description with O(log n)-bit wire indices, reading every description and input bit requires only O(n log n) bit queries. Thus any attempt to prove *superpolynomial bit-query hardness of reading the public description* fails immediately. This does **not** upper-bound the time needed to evaluate a general circuit after reading it.

**Crucial destruction control:** There is a deterministic O(n)-time classical decoder using the two-bit residue counter. Thus this is a restricted **depth/width** lower bound, not a quantum-versus-classical polynomial-time separation. The H–CCZ circuit here implements reversible classical logic.

## Reproducibility

Run from the repository root:

```sh
python -m unittest tests.test_public_mod3 -v
python -m tests.independent_attack007_audit
```

Local verification (12 November 2026): 8/8 new unit tests passed; 13/13 together with the existing exact H/CCZ backend tests. Exhaustive full-vector checks cover every input for n=1,...,6 (126 cases); 12 selected 12-qubit full-vector cases. A separate sparse exact simulator independently checked 74 full final states, while independent Boolean simulation checked all 4094 inputs for n=1,...,11. The 3-residual witness was checked for 96 lengths. A deliberately corrupted circuit was detected. These are finite audits of an all-n algebraic proof, not a replacement for it. No Lean attestation, hardware result or GitHub CI success is asserted without checking.

## Consequences

Attack 007 crosses the public-information boundary of the preceding sign-only estimator benchmark. It confirms a restricted-model white-box lower bound but **does not advance** an unrelativized BPP/BQP lower bound. The next target needs an explicit uniform H–CCZ family with a constant acceptance promise whose classical hardness survives *unrestricted* algebraic, Fourier, tensor-network and other polynomial-time preprocessing. Restriction-specific bounds must never be interpreted as full classical lower bounds.

## Prior art

- A. A. Razborov (1987) and R. Smolensky (1987), MOD_q not in AC^0[p] for distinct primes. For an exposition see O. Goldreich, *On teaching the approximation method for circuit lower bounds*, ECCC TR23-034 (2023): https://eccc.weizmann.ac.il/report/2023/034/ .
- D. Aharonov, *A Simple Proof that Toffoli and Hadamard are Quantum Universal*, arXiv:quant-ph/0301040 (2003).
- I. Markov and Y. Shi, *Simulating Quantum Computation by Contracting Tensor Networks*, SIAM J. Comput. 38 (2008).

**Final verdict:** RESTRICTED_PUBLIC_INPUT_MOD3_CERTIFIED / CLASSICAL_DECODER_PRESENT / BPP_VS_BQP_OPEN.
