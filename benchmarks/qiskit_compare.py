"""Reproducible, *non-ranking* PHYSQED-Q/Qiskit circuit comparison.

Qiskit is optional, and its performance/compatibility is never a proof of
quantum advantage. Unrepresentable outputs are explicitly uncheckable.
"""

import argparse
import importlib.metadata
import json
from pathlib import Path
import sys

from physqed_q.compiler import compile_circuit, metrics
from physqed_q.kernel import CircuitError, unitary, validate_circuit


SCHEMA = "physqed-q-qiskit-comparison-v1"
BASIS = ("h", "x", "z", "s", "sdg", "t", "tdg", "cx", "cz", "swap")
GATE_NAMES = {"h": "H", "x": "X", "z": "Z", "s": "S", "sdg": "SDG",
              "t": "T", "tdg": "TDG", "cx": "CNOT", "cz": "CZ",
              "swap": "SWAP"}
QISKIT_METHODS = {name: name for name in BASIS}
QISKIT_METHODS["cx"] = "cx"
MAX_BYTES = 256 * 1024


class BenchmarkError(ValueError):
    """The comparison cannot safely accept the input or external output."""


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise BenchmarkError(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def from_qiskit(circuit, name):
    """Convert a Qiskit circuit iff *exact* PHYSQED-Q semantics can describe it.

    Nonzero global phases are not discarded. Arbitrary parameter gates,
    measurements, custom operations and extra classical bits are rejected.
    """
    if circuit.num_clbits:
        raise BenchmarkError("unsupported classical bits or measurements")
    try:
        phase = float(circuit.global_phase)
    except (TypeError, ValueError, OverflowError) as exc:
        raise BenchmarkError("unsupported symbolic global phase") from exc
    if phase != 0.0:
        raise BenchmarkError("nonzero global phase is outside strict operator comparison")
    gates = []
    for entry in circuit.data:
        key = entry.operation.name
        if key not in GATE_NAMES or entry.operation.params:
            raise BenchmarkError(f"unsupported Qiskit output gate: {key}")
        targets = [circuit.find_bit(bit).index for bit in entry.qubits]
        gates.append({"gate": GATE_NAMES[key], "qubits": targets})
    try:
        return validate_circuit({"name": name, "qubits": circuit.num_qubits,
                                 "gates": gates})
    except CircuitError as exc:
        raise BenchmarkError(f"unsupported Qiskit output scope: {exc}") from exc


def _qiskit_metrics(circuit):
    ops = circuit.count_ops()
    return {
        "gates": int(circuit.size()),
        "depth": int(circuit.depth() or 0),
        "t_gates": int(ops.get("t", 0) + ops.get("tdg", 0)),
        "two_qubit_gates": sum(len(entry.qubits) == 2 for entry in circuit.data),
        "gate_histogram": {key: int(ops[key]) for key in sorted(ops)},
    }


def compare(raw, *, level=1, seed=2026):
    """Run fixed-basis Qiskit and PHYSQED-Q on the same bounded circuit."""
    if type(level) is not int or not 0 <= level <= 3:
        raise BenchmarkError("optimization level must be an integer 0..3")
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise BenchmarkError("seed must be an unsigned 32-bit integer")
    try:
        source = validate_circuit(raw)
    except CircuitError as exc:
        raise BenchmarkError(f"invalid source circuit: {exc}") from exc
    if source["qubits"] == 0:
        raise BenchmarkError("Qiskit baseline requires at least one qubit")
    try:
        from qiskit import QuantumCircuit, transpile
    except ImportError as exc:
        raise BenchmarkError("optional Qiskit not installed; install qiskit==2.6.1") from exc

    original = QuantumCircuit(source["qubits"])
    for gate in source["gates"]:
        kind = "cx" if gate["gate"] == "CNOT" else gate["gate"].lower()
        getattr(original, QISKIT_METHODS[kind])(*gate["qubits"])
    output = transpile(original, basis_gates=list(BASIS),
                       optimization_level=level, seed_transpiler=seed)

    certificate = compile_circuit(source)
    measured = {
        "schema": SCHEMA,
        "input_name": source["name"],
        "qubits": source["qubits"],
        "settings": {"optimization_level": level, "seed_transpiler": seed,
                     "basis_gates": list(BASIS), "backend": None,
                     "coupling_map": None},
        "physqed_q": {
            "version": "0.1.0",
            "input_metrics": metrics(source),
            "optimized_metrics": certificate["metrics"]["optimized"],
            "rewrites_exactly_replayed": len(certificate["steps"]),
        },
        "qiskit": {
            "version": importlib.metadata.version("qiskit"),
            "output_metrics": _qiskit_metrics(output),
            "exact_operator_equivalent": None,
            "status": "not_checkable",
            "reason": None,
            "global_phase_reported": str(output.global_phase),
        },
        "disclaimer": "Observed resource metrics only; no quantum advantage or general compiler superiority claim.",
    }
    try:
        translated = from_qiskit(output, source["name"])
    except BenchmarkError as exc:
        measured["qiskit"]["reason"] = str(exc)
    else:
        same = unitary(source) == unitary(translated)
        measured["qiskit"]["exact_operator_equivalent"] = same
        measured["qiskit"]["status"] = (
            "exact_operator_equivalent" if same else "operator_mismatch_or_phase"
        )
        if not same:
            measured["qiskit"]["reason"] = (
                "Output differs under strict full-operator equality; this alone does not imply a Qiskit bug"
            )
    return measured


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="PHYSQED-Q circuit JSON")
    parser.add_argument("--level", type=int, choices=range(4), default=1)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args(argv)
    try:
        with args.input.open("rb") as handle:
            payload = handle.read(MAX_BYTES + 1)
        if len(payload) > MAX_BYTES:
            raise BenchmarkError("JSON input exceeds 256 KiB")
        raw = json.loads(payload.decode("utf-8"),
                         object_pairs_hook=_reject_duplicate_keys)
        result = compare(raw, level=args.level, seed=args.seed)
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        print(f"BENCHMARK REJECTED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
