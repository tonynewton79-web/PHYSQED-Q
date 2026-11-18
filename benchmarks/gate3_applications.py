"""Locked 2-4-qubit application-style circuits for noisy Gate 3.

These are transparent synthetic analogues of GHZ preparation, graph states,
one-layer path MaxCut QAOA (angles chosen exactly within Clifford+T), and
two-step transverse-field Ising Trotter evolution, plus control-phase
cancellation tests. They are NOT independently sourced experimental workloads.
No results from noisy simulation influence these circuit definitions.
"""
import hashlib
import json


def g(name, *qubits):
    return {"gate": name, "qubits": list(qubits)}


def _case(family, n, gates):
    name = f"{family}-n{n}"
    return {"name": name, "family": family,
            "circuit": {"name": name, "qubits": n, "gates": gates}}


def corpus():
    result = []
    for n in (2, 3, 4):
        # GHZ preparation: H_0 CNOT_01 CNOT_12 ...
        gates = [g("H", 0)] + [g("CNOT", k - 1, k) for k in range(1, n)]
        result.append(_case("ghz", n, gates))

        # Linear cluster/graph-state preparation.
        gates = [g("H", k) for k in range(n)]
        gates += [g("CZ", k, k + 1) for k in range(n - 1)]
        result.append(_case("cluster", n, gates))

        # QAOA p=1 for path MaxCut: gamma = beta = pi/8.
        # Up to an overall phase: exp(-i gamma ZiZj) = CNOT T CNOT;
        # exp(-i beta Xi) = H T H. Objective sign conventions declared.
        gates = [g("H", k) for k in range(n)]
        for k in range(n - 1):
            gates += [g("CNOT", k, k + 1), g("T", k + 1),
                      g("CNOT", k, k + 1)]
        for k in range(n):
            gates += [g("H", k), g("T", k), g("H", k)]
        result.append(_case("qaoa-path", n, gates))

        # Two first-order Trotter steps of nearest-neighbour ZZ + X terms,
        # with quarter-pi phase rotations; exact Clifford+T circuit only.
        gates = [g("H", 0), g("X", n - 1)]
        for step in range(2):
            for k in range(n - 1):
                gates += [g("CNOT", k, k + 1),
                          g("T" if step == 0 else "TDG", k + 1),
                          g("CNOT", k, k + 1)]
            for k in range(n):
                gates += [g("H", k), g("T" if step == 0 else "TDG", k),
                          g("H", k)]
        result.append(_case("trotter-ising", n, gates))

        # Clean phase-cancellation control (the new v3 semantic lane).
        gates = [g("H", 0), g("T", 0), g("CNOT", 0, 1)]
        if n >= 3:
            gates.append(g("CZ", 0, 2))
        if n == 4:
            gates.append(g("CNOT", 0, 3))
        gates += [g("TDG", 0), g("H", 0)]
        result.append(_case("phase-cancel", n, gates))
    return result


def manifest():
    rows = corpus()
    payload = json.dumps(rows, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True).encode("ascii")
    return {"schema": "physqed-q-gate3-applications-v1",
            "sha256": hashlib.sha256(payload).hexdigest(),
            "case_count": len(rows),
            "family_count": {family: sum(r["family"] == family for r in rows)
                             for family in ("ghz", "cluster", "qaoa-path",
                                            "trotter-ising", "phase-cancel")},
            "qubits": [2, 3, 4],
            "independently_supplied_real_circuits": False}


if __name__ == "__main__":
    print(json.dumps(manifest(), sort_keys=True, indent=2))
