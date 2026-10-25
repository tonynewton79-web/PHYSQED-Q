"""Deterministic circuit rewrites and fail-closed replayable receipts.

The semantic checker executes the exact bounded operator; it is not Lean.
SHA-256 is an integrity digest and never a signature of authorship.
"""

import hashlib
import json
from types import MappingProxyType

from .kernel import MAX_GATES, CircuitError, unitary, unitary_digest, validate_circuit


RECEIPT_SCHEMA = "physqed-q-exact-receipt-v1"
SCOPE = {
    "kernel": "exact operator equality in Q(sqrt(2),i); at most four qubits",
    "lean_kernel_verified": False,
    "hardware_verified": False,
    "quantum_advantage_demonstrated": False,
    "integrity_not_authenticity": True,
}
RECEIPT_SCHEMA_V2 = "physqed-q-exact-receipt-v2"
V2_SCOPE = MappingProxyType({
    "kernel": "exact operator equality in Q(sqrt(2),i); at most four qubits",
    "lean_kernel_verified": False,
    "hardware_verified": False,
    "quantum_advantage_demonstrated": False,
    "integrity_not_authenticity": True,
    "optimizer": "commuting-disjoint-v1",
})
MAX_COMMUTING_STEPS = MAX_GATES * MAX_GATES + MAX_GATES


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


def _commuting_rewrites(gates):
    """Derive canonical moves; swaps only expose an existing two-gate rule.

    Adjacent reductions take priority. Otherwise the increasing (i, j) search
    picks a reducible pair, bubbles its right gate left, reduces, and restarts.
    There are no free-standing sorting swaps or arbitrary commuting loops.
    """
    current = gates
    count = 0
    while True:
        moves = []
        for at in range(len(current)):
            found = _replacement(current, at)
            if found is not None:
                moves.append((at, found))
                break
        if not moves:
            for i in range(len(current)):
                for j in range(i + 2, len(current)):
                    found = _replacement([current[i], current[j]], 0)
                    if found is None:
                        continue
                    support = set(current[i]["qubits"]) | set(current[j]["qubits"])
                    if any(support.intersection(g["qubits"]) for g in current[i + 1:j]):
                        continue
                    # Store only positions: each swap uses the updated word.
                    moves = [(at, None) for at in range(j - 1, i, -1)]
                    moves.append((i, found))
                    break
                if moves:
                    break
        if not moves:
            return
        for at, found in moves:
            if count >= MAX_COMMUTING_STEPS:
                raise CertificateError("unbounded trace")
            if found is None:
                found = ("commute_disjoint", 2, [current[at + 1], current[at]])
            current, step = _step(current, at, found)
            count += 1
            yield current, step


def _compile_commuting(raw):
    source = validate_circuit(raw)
    current = source["gates"]
    trace = []
    for current, step in _commuting_rewrites(current):
        trace.append(step)
    optimized = _with_gates(source, current)
    document = {
        "schema": RECEIPT_SCHEMA_V2,
        "input": source,
        "optimized": optimized,
        "steps": trace,
        "operator_sha256": unitary_digest(source),
        "metrics": {"input": metrics(source), "optimized": metrics(optimized)},
        "scope": dict(V2_SCOPE),
    }
    document["receipt_sha256"] = _hash(document)
    verify_receipt(document)
    return document


def compile_circuit(raw, *, optimizer="adjacent"):
    """Generate a candidate receipt, subject to mandatory exact replay."""
    if optimizer == "commuting":
        return _compile_commuting(raw)
    if optimizer != "adjacent":
        raise CertificateError("unsupported optimizer")
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


def _verify_adjacent_receipt(receipt):
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


def _has_fields(value, fields):
    # Check cardinality before constructing a set from untrusted keys.
    return type(value) is dict and len(value) == len(fields) and set(value) == fields


def _is_sha256(value):
    return (type(value) is str and len(value) == 64 and
            all(c in "0123456789abcdef" for c in value))


def _bounded_circuit(raw):
    """Bound every circuit field before copying or canonical serialization."""
    if not _has_fields(raw, {"name", "qubits", "gates"}):
        raise CertificateError("invalid circuit shape")
    if (type(raw["name"]) is not str or not 1 <= len(raw["name"]) <= 120 or
            type(raw["qubits"]) is not int or not 0 <= raw["qubits"] <= 4 or
            type(raw["gates"]) is not list or len(raw["gates"]) > MAX_GATES):
        raise CertificateError("invalid bounded circuit")
    for operation in raw["gates"]:
        if not _has_fields(operation, {"gate", "qubits"}):
            raise CertificateError("invalid gate shape")
        if (type(operation["gate"]) is not str or not 1 <= len(operation["gate"]) <= 4 or
                type(operation["qubits"]) is not list or len(operation["qubits"]) > 2 or
                any(type(q) is not int or not 0 <= q < raw["qubits"]
                    for q in operation["qubits"])):
            raise CertificateError("invalid bounded gate")
    try:
        return validate_circuit(raw)
    except CircuitError as exc:
        raise CertificateError("invalid circuit") from exc


def _validate_v2_shape(receipt):
    """Reject unbounded/nested values before any receipt hashing.

    Every accepted leaf has a fixed type and size, and every container has a
    fixed shape or a checked length. In particular no arbitrary nested value
    can reach JSON serialization, even when the public digest is already wrong.
    """
    required = {"schema", "input", "optimized", "steps", "operator_sha256",
                "metrics", "scope", "receipt_sha256"}
    if not _has_fields(receipt, required):
        raise CertificateError("unknown receipt fields")
    scope = receipt["scope"]
    if not _has_fields(scope, set(V2_SCOPE)) or any(
            type(scope[k]) is not type(v) or scope[k] != v for k, v in V2_SCOPE.items()):
        raise CertificateError("unsupported receipt scope/schema")
    claimed_steps = receipt["steps"]
    if type(claimed_steps) is not list or len(claimed_steps) > MAX_COMMUTING_STEPS:
        raise CertificateError("unbounded trace")
    for step in claimed_steps:
        if not _has_fields(step, {"rule", "index", "before_sha256", "after_sha256"}):
            raise CertificateError("invalid trace record shape")
        if (type(step["rule"]) is not str or not 1 <= len(step["rule"]) <= 32 or
                type(step["index"]) is not int or not 0 <= step["index"] < MAX_GATES or
                not _is_sha256(step["before_sha256"]) or
                not _is_sha256(step["after_sha256"])):
            raise CertificateError("invalid trace record values")
    claimed_metrics = receipt["metrics"]
    if not _has_fields(claimed_metrics, {"input", "optimized"}):
        raise CertificateError("invalid metrics shape")
    for value in claimed_metrics.values():
        if (not _has_fields(value, {"gates", "depth", "t_gates", "two_qubit_gates"}) or
                any(type(n) is not int or not 0 <= n <= MAX_GATES for n in value.values())):
            raise CertificateError("invalid bounded metrics")
    if not _is_sha256(receipt["operator_sha256"]) or not _is_sha256(receipt["receipt_sha256"]):
        raise CertificateError("invalid receipt digest shape")
    return _bounded_circuit(receipt["input"]), _bounded_circuit(receipt["optimized"])


def verify_receipt(receipt):
    """Verify untrusted v1 receipts unchanged, or replay the versioned v2 policy."""
    if not isinstance(receipt, dict) or receipt.get("schema") != RECEIPT_SCHEMA_V2:
        return _verify_adjacent_receipt(receipt)
    source, target = _validate_v2_shape(receipt)
    if type(receipt["receipt_sha256"]) is not str or _hash({
        k: v for k, v in receipt.items() if k != "receipt_sha256"
    }) != receipt["receipt_sha256"]:
        raise CertificateError("receipt integrity digest mismatch")
    try:
        if source != receipt["input"] or target != receipt["optimized"]:
            raise CertificateError("noncanonical circuit in receipt")
        if source["name"] != target["name"] or source["qubits"] != target["qubits"]:
            raise CertificateError("circuit context changed")
        claimed_steps = receipt["steps"]
        current = source["gates"]
        checked = 0
        for next_gates, expected in _commuting_rewrites(current):
            if checked >= len(claimed_steps):
                raise CertificateError("trace ends before deterministic normalization")
            claimed = claimed_steps[checked]
            if type(claimed) is not dict or _hash(claimed) != _hash(expected):
                raise CertificateError("rewrite trace mismatch")
            if unitary(_with_gates(source, current)) != unitary(_with_gates(source, next_gates)):
                raise CertificateError("rewrite not exactly unitary-equivalent")
            current = next_gates
            checked += 1
        if checked != len(claimed_steps):
            raise CertificateError("spurious rewrite step")
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
        raise CertificateError("invalid circuit or trace") from exc
    return {
        "verified": True,
        "scope": "bounded exact circuit-operator equivalence",
        "rewrites_checked": checked,
        "operator_sha256": actual_operator,
        "lean_kernel_verified": False,
        "hardware_verified": False,
    }
