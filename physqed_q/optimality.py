"""Finite one-qubit minimum certificates, relative to the exact kernel.

The planner and checker enumerate independently. Neither is a Lean or physical
verification; the digest detects corruption, not authorship.
"""
from types import MappingProxyType

from . import kernel
from .compiler import CertificateError, _hash


SCHEMA = "physqed-q-bounded-optimality-v1"
ALPHABET = ("H", "X", "Z", "S", "SDG", "T", "TDG")
OBJECTIVE = ("total_gates", "t_gates", "alphabet_lexicographic")
SCOPE = MappingProxyType({
    "claim": "bounded exact one-qubit gate-count minimum",
    "lean_kernel_verified": False,
    "hardware_verified": False,
    "quantum_advantage_demonstrated": False,
    "integrity_not_authenticity": True,
})


class OptimalityError(CertificateError):
    """Unsupported bounded search or invalid optimality evidence."""


def _fields(value, expected):
    # Reject oversized containers before examining their keys or values.
    return (type(value) is dict and len(value) == len(expected)
            and all(type(key) is str for key in value) and set(value) == expected)


def _horizon(value):
    if type(value) is not int or not 0 <= value <= 5:
        raise OptimalityError("horizon must be a built-in integer in [0,5]")
    return value


def _bounded_circuit(raw, limit):
    """Bound all nested data before delegating semantic validation."""
    if not _fields(raw, {"name", "qubits", "gates"}):
        raise OptimalityError("invalid circuit fields")
    if (type(raw["name"]) is not str or not 0 < len(raw["name"]) <= 120
            or not raw["name"].strip()):
        raise OptimalityError("invalid circuit name")
    if type(raw["qubits"]) is not int or raw["qubits"] != 1:
        raise OptimalityError("bounded optimality requires exactly one qubit")
    gates = raw["gates"]
    if type(gates) is not list or len(gates) > limit:
        raise OptimalityError("circuit exceeds gate bound")
    for operation in gates:
        if not _fields(operation, {"gate", "qubits"}):
            raise OptimalityError("invalid operation fields")
        kind, positions = operation["gate"], operation["qubits"]
        if type(kind) is not str or len(kind) > 3 or kind not in ALPHABET:
            raise OptimalityError("unsupported gate")
        if (type(positions) is not list or len(positions) != 1
                or type(positions[0]) is not int or positions[0] != 0):
            raise OptimalityError("invalid one-qubit operation")
    try:
        return kernel.validate_circuit(raw)
    except kernel.CircuitError as exc:
        raise OptimalityError("invalid circuit") from exc


def _validate_receipt(receipt):
    """Strict, bounded JSON shapes, checked in full before any hashing."""
    if not _fields(receipt, {"schema", "input", "optimized", "search",
                             "operator_sha256", "scope", "receipt_sha256"}):
        raise OptimalityError("unknown receipt fields")
    if type(receipt["schema"]) is not str or receipt["schema"] != SCHEMA:
        raise OptimalityError("unsupported receipt schema")
    search = receipt["search"]
    if not _fields(search, {"alphabet", "horizon", "objective", "words_examined",
                            "minimum_gates", "t_gates"}):
        raise OptimalityError("invalid search fields")
    horizon = _horizon(search["horizon"])
    for key, expected in (("alphabet", ALPHABET), ("objective", OBJECTIVE)):
        value = search[key]
        if (type(value) is not list or len(value) != len(expected)
                or any(type(item) is not str for item in value)
                or value != list(expected)):
            raise OptimalityError("unsupported search alphabet/objective")
    for key, bound in (("words_examined", sum(7 ** k for k in range(horizon + 1))),
                       ("minimum_gates", horizon), ("t_gates", horizon)):
        if type(search[key]) is not int or not 0 <= search[key] <= bound:
            raise OptimalityError("invalid search cost/count")
    scope = receipt["scope"]
    if not _fields(scope, set(SCOPE)):
        raise OptimalityError("invalid scope fields")
    if any(type(scope[key]) is not type(value) or scope[key] != value
           for key, value in SCOPE.items()):
        raise OptimalityError("unsupported receipt scope")
    for key in ("operator_sha256", "receipt_sha256"):
        value = receipt[key]
        if (type(value) is not str or len(value) != 64
                or any(char not in "0123456789abcdef" for char in value)):
            raise OptimalityError("invalid digest")
    source = _bounded_circuit(receipt["input"], 64)
    target = _bounded_circuit(receipt["optimized"], horizon)
    if source["name"] != target["name"]:
        raise OptimalityError("circuit context changed")
    return source, target, horizon


def _planner_search(operator, horizon):
    """Layered enumeration; keep every prefix, never quotient by operator."""
    layer = [((), ((kernel.ONE, kernel.ZERO), (kernel.ZERO, kernel.ONE)))]
    best = None
    examined = 0
    for length in range(horizon + 1):
        next_layer = []
        for word, columns in layer:
            examined += 1
            if columns == operator:
                cost = (length, sum(i >= 5 for i in word), word)
                if best is None or cost < best:
                    best = cost
            if length < horizon:
                for index, kind in enumerate(ALPHABET):
                    operation = {"gate": kind, "qubits": [0]}
                    advanced = tuple(kernel._apply(col, operation) for col in columns)
                    next_layer.append((word + (index,), advanced))
        layer = next_layer
    return best, examined


def certify_optimality(raw, *, horizon=5):
    """Certify an exhaustive finite minimum, or fail without a certificate."""
    horizon = _horizon(horizon)
    source = _bounded_circuit(raw, 64)
    best, examined = _planner_search(kernel.unitary(source), horizon)
    if best is None:
        raise OptimalityError("no exact representative within search horizon")
    optimized = {"name": source["name"], "qubits": 1, "gates": [
        {"gate": ALPHABET[index], "qubits": [0]} for index in best[2]]}
    receipt = {
        "schema": SCHEMA,
        "input": source,
        "optimized": optimized,
        "search": {"alphabet": list(ALPHABET), "horizon": horizon,
                   "objective": list(OBJECTIVE), "words_examined": examined,
                   "minimum_gates": best[0], "t_gates": best[1]},
        "operator_sha256": kernel.unitary_digest(source),
        "scope": dict(SCOPE),
    }
    receipt["receipt_sha256"] = _hash(receipt)
    verify_optimality(receipt)
    return receipt


def verify_optimality(receipt):
    """Recheck every bounded word without using the planner or its table."""
    source, target, horizon = _validate_receipt(receipt)
    unsigned = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    if _hash(unsigned) != receipt["receipt_sha256"]:
        raise OptimalityError("receipt integrity digest mismatch")
    actual_digest = kernel.unitary_digest(source)
    if receipt["operator_sha256"] != actual_digest:
        raise OptimalityError("source operator fingerprint mismatch")
    operator = kernel.unitary(source)
    if kernel.unitary(target) != operator:
        raise OptimalityError("full exact operator mismatch")
    best = None
    examined = 0

    def visit(word, columns, t_count):
        nonlocal best, examined
        examined += 1
        if columns == operator:
            cost = (len(word), t_count, word)
            if best is None or cost < best:
                best = cost
        if len(word) == horizon:
            return
        for rank, kind in enumerate(("H", "X", "Z", "S", "SDG", "T", "TDG")):
            operation = {"gate": kind, "qubits": [0]}
            evolved = (kernel._apply(columns[0], operation),
                       kernel._apply(columns[1], operation))
            visit(word + (rank,), evolved, t_count + (kind in {"T", "TDG"}))

    visit((), ((kernel.ONE, kernel.ZERO), (kernel.ZERO, kernel.ONE)), 0)
    winner = tuple(ALPHABET.index(g["gate"]) for g in target["gates"])
    if best != (len(winner), sum(i >= 5 for i in winner), winner):
        raise OptimalityError("winner is not the bounded exact minimum")
    search = receipt["search"]
    if (examined != sum(7 ** k for k in range(horizon + 1))
            or search["words_examined"] != examined
            or search["minimum_gates"] != best[0] or search["t_gates"] != best[1]):
        raise OptimalityError("search count/cost does not match exhaustive check")
    return {"verified": True, "scope": SCOPE["claim"],
            "words_examined": examined, "minimum_gates": best[0],
            "t_gates": best[1], "operator_sha256": actual_digest,
            "lean_kernel_verified": False, "hardware_verified": False,
            "quantum_advantage_demonstrated": False,
            "integrity_not_authenticity": True}
