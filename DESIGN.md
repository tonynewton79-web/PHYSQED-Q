# PHYSQED-Q — exact circuit certification MVP

**Status:** implementation specification for a bounded compiler prototype, not a physical quantum processor.

## Intent

Extend the independent PHYSQED verification programme with a quantum-circuit optimizer that produces replayable evidence for its exact semantics. The first consumer is a researcher who must distinguish a genuinely equivalent circuit transformation from a marketing claim, a sample-specific identity, or a hash-only receipt.

## Scope

- Accept strictly parsed declarative circuits of 0–4 qubits and up to 64 gates.
- Support `H`, `X`, `Z`, `S`, `SDG`, `T`, `TDG`, `CNOT`, `CZ`, and `SWAP` with explicit qubit order and no parameters.
- Evaluate complete finite circuit operators exactly in the number field Q(√2,i), never floating-point approximations.
- Optimize using a small named, reproducible rewrite catalogue: adjacent inverses; `S²=Z`, `T²=S` and their adjoints; `HZH=X`, `HXH=Z`.
- Produce an integrity-digested JSON receipt with source, optimized circuit, ordered rewrite trace, exact operator digest, gate/depth/T-count metrics and explicit scope flags.
- Provide an independent *replay entry point* that rejects a changed trace, bad claim, unsupported circuit, changed statistics, or fabricated receipt digest, and recomputes exact operator equality rather than trusting assertions.
- Provide CLI compile/verify/examples and a separate numerical oracle test suite; use Python's standard library only.

## Non-goals

- No physical quantum hardware, quantum speedup, scalable Shor factoring, Lean compilation, quantum noise model, hardware connectivity, authentication or MCP server in this MVP.
- Hashes establish byte-level integrity consistency, not origin/authenticity.
- Bounded exhaustive operator comparison establishes only equivalence within the explicitly implemented gate semantics; it is not a Lean-kernel proof.
- Strict operator equality is used, not equality up to a global phase.

## Approaches considered

1. **Exact full-operator replay (selected):** bounded but mathematically transparent, no package dependency, independent adversarial tests; exponential scaling explicitly capped.
2. Float-based numerical optimization: faster and larger, but cannot substantiate an *exact* equivalence claim.
3. Lean-first universal compiler: ultimately desirable, but a larger formalization with a new trusted bridge and no available Lean toolchain in the present environment.

## Inputs and result

Input JSON shape: `{"name":"example","qubits":2,"gates":[{"gate":"H","qubits":[0]},{"gate":"CNOT","qubits":[0,1]}]}`. `qubits` in a `CNOT` gate are `[control,target]` and qubit 0 is the least-significant basis bit.

The verifier returns an explicit success/failure status. It does not accept self-declared proof flags. `lean_kernel_verified` and `hardware_verified` are always `false`.

## Integration

The canonical standalone public repository is `tonynewton79-web/PHYSQED-Q`, with package, tests, examples, and documentation at the repository root. The original PHYSQED development branch and draft PR in `theoremlean` are preserved for provenance, not automatically merged. CI runs `unittest` without dependencies on `main` and pull requests.

## Acceptance

Tests must exercise Bell/GHZ amplitudes, `HZH=X`, T/S rewrites, exact equivalence for several circuits, order-sensitive CNOT, malformed/adversarial JSON, tampering of every certificate component, and the CLI round trip. Any request beyond the declared gate/qubit/budget class must fail closed.
