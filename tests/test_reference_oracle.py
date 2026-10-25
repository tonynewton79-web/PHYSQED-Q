"""Numerical oracle independently derives transitions from gate matrices.

This implementation uses built-in Python complex numbers only as a *test*
oracle; production certification remains exact arithmetic throughout.
"""
from fractions import Fraction
import math
from pathlib import Path
import random
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from physqed_q.compiler import compile_circuit, verify_receipt
from physqed_q.kernel import evolve


SQ = math.sqrt(0.5)
MATS = {
    "H": ((SQ, SQ), (SQ, -SQ)),
    "X": ((0, 1), (1, 0)),
    "Z": ((1, 0), (0, -1)),
    "S": ((1, 0), (0, 1j)),
    "SDG": ((1, 0), (0, -1j)),
    "T": ((1, 0), (0, complex(SQ, SQ))),
    "TDG": ((1, 0), (0, complex(SQ, -SQ))),
}


def reference(circuit, basis):
    n = circuit["qubits"]
    state = [complex(int(i == basis)) for i in range(1 << n)]
    for gate in circuit["gates"]:
        name, qubits = gate["gate"], gate["qubits"]
        updated = [0j] * len(state)
        for i, amp in enumerate(state):
            if name in MATS:
                q = qubits[0]
                for bit in (0, 1):
                    destination = (i & ~(1 << q)) | (bit << q)
                    updated[destination] += MATS[name][bit][(i >> q) & 1] * amp
            else:
                a, b = qubits
                if name == "CNOT":
                    destination = i ^ ((1 << b) if ((i >> a) & 1) else 0)
                    phase = 1
                elif name == "CZ":
                    destination = i
                    phase = -1 if ((i >> a) & (i >> b) & 1) else 1
                else:  # SWAP
                    destination = i ^ (((1 << a) | (1 << b))
                                       if ((i >> a) & 1) != ((i >> b) & 1) else 0)
                    phase = 1
                updated[destination] += phase * amp
        state = updated
    return state


def approximate(exact):
    a, b, c, d = [Fraction(x) for x in exact.coefficients()]
    return complex(float(a) + float(b) * math.sqrt(2),
                   float(c) + float(d) * math.sqrt(2))


class IndependentReferenceTests(unittest.TestCase):
    def test_seeded_random_circuits_against_direct_dense_gate_matrices(self):
        rng = random.Random(239104)
        for n in (1, 2, 3):
            for iteration in range(35):
                gates = []
                for unused in range(rng.randrange(1, 14)):
                    name = rng.choice(list(MATS) + (["CNOT", "CZ", "SWAP"] if n > 1 else []))
                    qubits = rng.sample(range(n), 2 if name in {"CNOT", "CZ", "SWAP"} else 1)
                    gates.append({"gate": name, "qubits": qubits})
                circuit = {"name": f"oracle-{n}-{iteration}", "qubits": n, "gates": gates}
                for basis in (0, (1 << n) - 1):
                    expected = reference(circuit, basis)
                    observed = evolve(circuit, basis)
                    for k, (want, have) in enumerate(zip(expected, observed)):
                        self.assertAlmostEqual(approximate(have).real, want.real, places=10,
                                               msg=(n, iteration, basis, k, gates))
                        self.assertAlmostEqual(approximate(have).imag, want.imag, places=10,
                                               msg=(n, iteration, basis, k, gates))

    def test_certified_optimization_preserves_independent_dense_operator(self):
        source = {"name": "two-channel witness", "qubits": 2, "gates": [
            {"gate": "H", "qubits": [0]}, {"gate": "X", "qubits": [0]},
            {"gate": "H", "qubits": [0]}, {"gate": "S", "qubits": [1]},
            {"gate": "S", "qubits": [1]}, {"gate": "CNOT", "qubits": [1, 0]},
            {"gate": "CNOT", "qubits": [1, 0]},
        ]}
        receipt = compile_circuit(source)
        self.assertTrue(verify_receipt(receipt)["verified"])
        for basis in range(4):
            original = reference(source, basis)
            optimized = reference(receipt["optimized"], basis)
            for a, b in zip(original, optimized):
                self.assertAlmostEqual(a.real, b.real, places=10)
                self.assertAlmostEqual(a.imag, b.imag, places=10)


if __name__ == "__main__":
    unittest.main()
