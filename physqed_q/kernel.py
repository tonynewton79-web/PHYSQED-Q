"""Bounded, exact quantum-circuit semantics in Q(sqrt(2), i).

No floating-point approximation, dynamic execution, or external dependency.
Qubit 0 is the least significant bit of the computational-basis index.
"""

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json


SCHEMA = "physqed-q-circuit-v1"
MAX_QUBITS = 4
MAX_GATES = 64
SINGLE = frozenset({"H", "X", "Z", "S", "SDG", "T", "TDG"})
DOUBLE = frozenset({"CNOT", "CZ", "SWAP"})


class CircuitError(ValueError):
    """Rejected untrusted declarative circuit or unsupported operation."""


@dataclass(frozen=True)
class Exact:
    """(a + b*sqrt(2)) + i*(c + d*sqrt(2)), with rational entries."""

    a: Fraction = Fraction(0)
    b: Fraction = Fraction(0)
    c: Fraction = Fraction(0)
    d: Fraction = Fraction(0)

    def __add__(self, other):
        return Exact(self.a + other.a, self.b + other.b,
                     self.c + other.c, self.d + other.d)

    def __neg__(self):
        return Exact(-self.a, -self.b, -self.c, -self.d)

    def __sub__(self, other):
        return self + (-other)

    def __mul__(self, other):
        def pair_mul(a, b, c, d):
            return a * c + 2 * b * d, a * d + b * c

        rr = pair_mul(self.a, self.b, other.a, other.b)
        ii = pair_mul(self.c, self.d, other.c, other.d)
        ri = pair_mul(self.a, self.b, other.c, other.d)
        ir = pair_mul(self.c, self.d, other.a, other.b)
        return Exact(rr[0] - ii[0], rr[1] - ii[1],
                     ri[0] + ir[0], ri[1] + ir[1])

    def coefficients(self):
        return tuple(str(x) for x in (self.a, self.b, self.c, self.d))


ZERO = Exact()
ONE = Exact(Fraction(1))
NEG_ONE = -ONE
IMAG = Exact(c=Fraction(1))
NEG_IMAG = -IMAG
INV_ROOT_TWO = Exact(b=Fraction(1, 2))
T_PHASE = Exact(b=Fraction(1, 2), d=Fraction(1, 2))
TDG_PHASE = Exact(b=Fraction(1, 2), d=Fraction(-1, 2))


def validate_circuit(raw):
    """Return a fresh canonical circuit, refusing implicit types and extra keys."""
    if not isinstance(raw, dict) or set(raw) != {"name", "qubits", "gates"}:
        raise CircuitError("circuit must have exactly name, qubits and gates")
    name = raw["name"]
    count = raw["qubits"]
    gates = raw["gates"]
    if not isinstance(name, str) or not name.strip() or len(name) > 120:
        raise CircuitError("name must be nonempty and at most 120 characters")
    if type(count) is not int or not 0 <= count <= MAX_QUBITS:
        raise CircuitError("qubits must be an integer in [0,4]")
    if not isinstance(gates, list) or len(gates) > MAX_GATES:
        raise CircuitError("gates must be an array of at most 64 entries")
    normalized = []
    for index, item in enumerate(gates):
        if not isinstance(item, dict) or set(item) != {"gate", "qubits"}:
            raise CircuitError(f"gate {index} has an invalid shape")
        kind = item["gate"]
        positions = item["qubits"]
        if type(kind) is not str:
            raise CircuitError(f"gate {index} must have a string kind")
        width = 1 if kind in SINGLE else 2 if kind in DOUBLE else None
        if width is None:
            raise CircuitError(f"gate {index} unsupported")
        if not isinstance(positions, list) or len(positions) != width:
            raise CircuitError(f"gate {index} has wrong arity")
        if any(type(q) is not int or q < 0 or q >= count for q in positions):
            raise CircuitError(f"gate {index} has invalid qubit index")
        if len(set(positions)) != len(positions):
            raise CircuitError(f"gate {index} repeats a qubit")
        normalized.append({"gate": kind, "qubits": list(positions)})
    return {"name": name, "qubits": count, "gates": normalized}


def _apply(state, operation):
    """One unitary on amplitudes; no rule here refers to optimizer patterns."""
    kind = operation["gate"]
    qs = operation["qubits"]
    first = 1 << qs[0]
    out = list(state)
    if kind == "H":
        for k in range(len(state)):
            if not k & first:
                j = k | first
                out[k] = INV_ROOT_TWO * (state[k] + state[j])
                out[j] = INV_ROOT_TWO * (state[k] - state[j])
    elif kind == "X":
        for k in range(len(state)):
            if not k & first:
                j = k | first
                out[k], out[j] = state[j], state[k]
    elif kind in {"Z", "S", "SDG", "T", "TDG"}:
        phase = {"Z": NEG_ONE, "S": IMAG, "SDG": NEG_IMAG,
                 "T": T_PHASE, "TDG": TDG_PHASE}[kind]
        for k in range(len(state)):
            if k & first:
                out[k] = phase * state[k]
    elif kind == "CZ":
        second = 1 << qs[1]
        for k in range(len(state)):
            if k & first and k & second:
                out[k] = -state[k]
    elif kind == "CNOT":
        second = 1 << qs[1]
        for k in range(len(state)):
            if k & first:
                out[k ^ second] = state[k]
    elif kind == "SWAP":
        second = 1 << qs[1]
        for k in range(len(state)):
            if bool(k & first) != bool(k & second):
                out[k ^ first ^ second] = state[k]
    else:
        raise CircuitError("unsupported gate at execution")
    return tuple(out)


def evolve(circuit, basis_index=0):
    canonical = validate_circuit(circuit)
    size = 1 << canonical["qubits"]
    if type(basis_index) is not int or not 0 <= basis_index < size:
        raise CircuitError("basis index outside Hilbert space")
    state = [ZERO] * size
    state[basis_index] = ONE
    for operation in canonical["gates"]:
        state = _apply(state, operation)
    return tuple(state)


def unitary(circuit):
    canonical = validate_circuit(circuit)
    return tuple(evolve(canonical, j) for j in range(1 << canonical["qubits"]))


def unitary_digest(circuit):
    columns = [[list(x.coefficients()) for x in col] for col in unitary(circuit)]
    raw = json.dumps(columns, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return hashlib.sha256(raw).hexdigest()
