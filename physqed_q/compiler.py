"""Deterministic circuit rewrites and fail-closed replayable receipts.

The semantic checker executes the exact bounded operator; it is not Lean.
SHA-256 is an integrity digest and never a signature of authorship.
"""

import hashlib
import json

from .kernel import CircuitError, unitary, unitary_digest, validate_circuit


RECEIPT_SCHEMA = "physqed-q-exact-receipt-v1"
SCOPE = {
    "kernel": "exact operator equality in Q(sqrt(2),i); at most four qubits",
    "lean_kernel_verified": False,
    "hardware_verified": False,
    "quantum_advantage_demonstrated": False,
    "integrity_not_authenticity": True,
}


class CertificateError(ValueError):
    """The evidence does not validate under the supported exact semantics."""


def _hash(data):
    try:
        raw = json.dumps(data, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True, allow_nan=False).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError, RecursionError) as exc:
        raise CertificateError("receipt contains noncanonical data") from exc
    return hashlib.sha256(raw).hexdigest()


def metrics(circuit):
    canonical = validate_circuit(circuit)
    last = [0] * canonical["qubits"]
    for operation in canonical["gates"]:
        affected = operation["qubits"]
        step = 1 + max(last[q] for q in affected)
        for q in affected:
            last[q] = step
    return {
        "gates": len(canonical["gates"]),
        "depth": max(last, default=0),
        "t_gates": sum(g["gate"] in {"T", "TDG"} for g in canonical["gates"]),
        "two_qubit_gates": sum(len(g["qubits"]) == 2 for g in canonical["gates"]),
    }


def _replacement(gates, at):
    """Return (rule, consumed, replacements), or None. Rules are exact, not up to phase."""
    if at + 1 < len(gates):
        a, b = gates[at:at + 2]
        first, second = a["gate"], b["gate"]
        if a["qubits"] == b["qubits"]:
            inverse = {
                "H": "H", "X": "X", "Z": "Z", "CNOT": "CNOT",
                "CZ": "CZ", "SWAP": "SWAP", "S": "SDG", "SDG": "S",
                "T": "TDG", "TDG": "T",
            }
            if inverse.get(first) == second:
                return (f"{first}_inverse", 2, [])
            square = {"S": "Z", "SDG": "Z", "T": "S", "TDG": "SDG"}
            if first == second and first in square:
                return (f"{first}{second}_to_{square[first]}", 2,
                        [{"gate": square[first], "qubits": list(a["qubits"])}])
    if at + 2 < len(gates):
        a, b, c = gates[at:at + 3]
        if a["gate"] == c["gate"] == "H" and b["gate"] in {"X", "Z"}:
            if a["qubits"] == b["qubits"] == c["qubits"]:
                swapped = "X" if b["gate"] == "Z" else "Z"
                return (f"H{b['gate']}H_to_{swapped}", 3,
                        [{"gate": swapped, "qubits": list(a["qubits"])}])
    return None


def _step(gates, at, found):
    rule, consumed, output = found
    next_gates = gates[:at] + output + gates[at + consumed:]
    return next_gates, {
        "rule": rule,
        "index": at,
        "before_sha256": _hash(gates),
        "after_sha256": _hash(next_gates),
    }


def _with_gates(original, gates):
    return {"name": original["name"], "qubits": original["qubits"], "gates": gates}


def compile_circuit(raw):
    """Generate a candidate receipt, subject to mandatory exact replay."""
    source = validate_circuit(raw)
    current = [dict(gate=g["gate"], qubits=list(g["qubits"])) for g in source["gates"]]
    trace = []
    while True:
        matched = False
        for at in range(len(current)):
            found = _replacement(current, at)
            if found is None:
                continue
            current, step = _step(current, at, found)
            trace.append(step)
            matched = True
            break
        if not matched:
            break
    optimized = _with_gates(source, current)
    document = {
        "schema": RECEIPT_SCHEMA,
        "input": source,
        "optimized": optimized,
        "steps": trace,
        "operator_sha256": unitary_digest(source),
        "metrics": {"input": metrics(source), "optimized": metrics(optimized)},
        "scope": dict(SCOPE),
    }
    document["receipt_sha256"] = _hash(document)
    verify_receipt(document)
    return document


def verify_receipt(receipt):
    """Replay the claimed rewrites, checking actual exact operators at each step.

    All fields are treated as untrusted.  In particular `verified` is not
    accepted as an input field and a valid digest alone confers no status.
    """
    required = {"schema", "input", "optimized", "steps", "operator_sha256",
                "metrics", "scope", "receipt_sha256"}
    if not isinstance(receipt, dict) or set(receipt) != required:
        raise CertificateError("unknown receipt fields")
    if receipt["schema"] != RECEIPT_SCHEMA or _hash(receipt["scope"]) != _hash(SCOPE):
        raise CertificateError("unsupported receipt scope/schema")
    if type(receipt["receipt_sha256"]) is not str or _hash({
        k: v for k, v in receipt.items() if k != "receipt_sha256"
    }) != receipt["receipt_sha256"]:
        raise CertificateError("receipt integrity digest mismatch")
    try:
        source = validate_circuit(receipt["input"])
        target = validate_circuit(receipt["optimized"])
        if source != receipt["input"] or target != receipt["optimized"]:
            raise CertificateError("noncanonical circuit in receipt")
        if source["name"] != target["name"] or source["qubits"] != target["qubits"]:
            raise CertificateError("circuit context changed")
        claimed_steps = receipt["steps"]
        if not isinstance(claimed_steps, list) or len(claimed_steps) > 64:
            raise CertificateError("unbounded trace")
        current = source["gates"]
        for claimed in claimed_steps:
            # A deterministic normal-form trace always takes the first leftmost match.
            at = next((i for i in range(len(current)) if _replacement(current, i)), None)
            if at is None:
                raise CertificateError("spurious rewrite step")
            next_gates, expected = _step(current, at, _replacement(current, at))
            if type(claimed) is not dict or _hash(claimed) != _hash(expected):
                raise CertificateError("rewrite trace mismatch")
            if unitary(_with_gates(source, current)) != unitary(_with_gates(source, next_gates)):
                raise CertificateError("rewrite not exactly unitary-equivalent")
            current = next_gates
        if any(_replacement(current, i) for i in range(len(current))):
            raise CertificateError("trace ends before deterministic normalization")
        if current != target["gates"]:
            raise CertificateError("output differs from trace")
        actual_operator = unitary_digest(source)
        if receipt["operator_sha256"] != actual_operator:
            raise CertificateError("source operator fingerprint mismatch")
        if unitary(source) != unitary(target):
            raise CertificateError("full exact operator mismatch")
        if _hash(receipt["metrics"]) != _hash({
            "input": metrics(source), "optimized": metrics(target)
        }):
            raise CertificateError("metrics do not match circuit")
    except (CircuitError, TypeError, AttributeError, KeyError, IndexError) as exc:
        if isinstance(exc, CertificateError):
            raise
        raise CertificateError("invalid circuit or trace") from exc
    return {
        "verified": True,
        "scope": "bounded exact circuit-operator equivalence",
        "rewrites_checked": len(claimed_steps),
        "operator_sha256": actual_operator,
        "lean_kernel_verified": False,
        "hardware_verified": False,
    }
