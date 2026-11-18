"""Deterministic internal T-count ablation, NOT an external compiler ranking.

Compares original adjacent / v2 disjoint / v3 phase policies and verifies
all output operators. Only exact logical resource counts are measured.
"""
import json

from physqed_q.compiler import compile_circuit, verify_receipt


def g(label, *qubits):
    return {"gate": label, "qubits": list(qubits)}


def cases():
    return [
        ("control-CNOT", 2, [g("T", 0), g("CNOT", 0, 1), g("TDG", 0)]),
        ("target-CNOT-negative", 2, [g("T", 1), g("CNOT", 0, 1), g("TDG", 1)]),
        ("CZ-diagonal", 2, [g("T", 1), g("CZ", 0, 1), g("TDG", 1)]),
        ("H-barrier-negative", 2, [g("T", 0), g("H", 0), g("TDG", 0)]),
        ("three-CNOTs", 3, [g("T", 0), g("CNOT", 0, 1),
                            g("CNOT", 0, 2), g("TDG", 0)]),
        ("four-qubit-control", 4, [g("T", 0), g("CZ", 0, 3),
                                  g("CNOT", 0, 2), g("TDG", 0)]),
    ]


def run():
    rows = []
    for name, width, gates in cases():
        raw = {"name": name, "qubits": width, "gates": gates}
        results = {}
        for policy in ("adjacent", "commuting", "phase"):
            receipt = compile_circuit(raw, optimizer=policy)
            replay = verify_receipt(receipt)
            assert replay["verified"]
            results[policy] = {
                "gates": receipt["metrics"]["optimized"]["gates"],
                "depth": receipt["metrics"]["optimized"]["depth"],
                "t_gates": receipt["metrics"]["optimized"]["t_gates"],
                "two_qubit_gates": receipt["metrics"]["optimized"]["two_qubit_gates"],
                "steps": len(receipt["steps"]),
                "replayed": replay["verified"],
            }
        rows.append({"case": name, "qubits": width, "input_gates": len(gates),
                     "policies": results, "phase_minus_commuting_t_count":
                     results["phase"]["t_gates"]-results["commuting"]["t_gates"]})
    return {"schema": "physqed-q-phase-internal-ablation-v1",
            "external_ranking": False, "physical_cost_measured": False,
            "not_a_qiskit_comparison": True, "cases": rows}


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
