"""Fixed internal adjacent-vs-commuting corpus; no optional dependencies."""

import json
from pathlib import Path

from physqed_q.compiler import compile_circuit, metrics, verify_receipt


def run_suite():
    """Measure both policies and independently replay every generated receipt.

    Raw circuit words and receipt digests make each result reproducible. Any
    compilation or replay error propagates rather than becoming a success flag.
    """
    fixture = Path(__file__).resolve().parents[1] / "examples" / "commuting.json"
    with fixture.open(encoding="utf-8") as stream:
        witness = json.load(stream)
    corpus = [
        ("disjoint_inverse", witness),
        ("adjacent_parity", {
            "name": "Adjacent T-square parity",
            "qubits": 2,
            "gates": [{"gate": "T", "qubits": [0]},
                      {"gate": "T", "qubits": [0]}],
        }),
        ("blocked_overlap", {
            "name": "Overlapping CNOT blocks H cancellation",
            "qubits": 2,
            "gates": [{"gate": "H", "qubits": [0]},
                      {"gate": "CNOT", "qubits": [0, 1]},
                      {"gate": "H", "qubits": [0]}],
        }),
    ]
    cases = []
    for name, source in corpus:
        case = {"id": name, "input": source, "input_metrics": metrics(source)}
        for version, optimizer in [("v1", "adjacent"), ("v2", "commuting")]:
            receipt = compile_circuit(source, optimizer=optimizer)
            replay = verify_receipt(receipt)
            case[version] = {
                "optimizer": optimizer,
                "receipt_schema": receipt["schema"],
                "receipt_sha256": receipt["receipt_sha256"],
                "optimized": receipt["optimized"],
                "metrics": metrics(receipt["optimized"]),
                "exact_operator_verified": replay["verified"],
                "rewrites_checked": replay["rewrites_checked"],
            }
        case["v2_minus_v1"] = {
            key: case["v2"]["metrics"][key] - case["v1"]["metrics"][key]
            for key in case["v1"]["metrics"]
        }
        cases.append(case)
    return {"schema": "physqed-q-internal-commuting-benchmark-v1", "cases": cases}


if __name__ == "__main__":
    print(json.dumps(run_suite(), indent=2, sort_keys=True, allow_nan=False))
