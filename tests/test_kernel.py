"""Quantum semantics tests with independently derived finite-state expectations."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from physqed_q.kernel import CircuitError, evolve, unitary, unitary_digest, validate_circuit


def circuit(n, *items):
    return {"name": "reference", "qubits": n, "gates": [
        {"gate": name, "qubits": list(qubits)} for name, qubits in items
    ]}


def entries(state):
    return [x.coefficients() for x in state]


ZERO = ("0", "0", "0", "0")
ONE = ("1", "0", "0", "0")
ROOT_HALF = ("0", "1/2", "0", "0")


class QuantumKernelTests(unittest.TestCase):
    def test_bell_state_has_only_00_and_11_amplitudes(self):
        bell = circuit(2, ("H", (0,)), ("CNOT", (0, 1)))
        self.assertEqual(entries(evolve(bell)), [ROOT_HALF, ZERO, ZERO, ROOT_HALF])

    def test_ghz_three_qubit_support(self):
        ghz = circuit(3, ("H", (0,)), ("CNOT", (0, 1)), ("CNOT", (0, 2)))
        observed = entries(evolve(ghz))
        self.assertEqual([i for i, a in enumerate(observed) if a != ZERO], [0, 7])
        self.assertEqual(observed[0], ROOT_HALF)
        self.assertEqual(observed[7], ROOT_HALF)

    def test_hadamard_is_its_own_inverse_and_hzh_equals_x(self):
        identity = circuit(1)
        self.assertEqual(unitary(circuit(1, ("H", (0,)), ("H", (0,)))), unitary(identity))
        self.assertEqual(unitary(circuit(1, ("H", (0,)), ("Z", (0,)), ("H", (0,)))),
                         unitary(circuit(1, ("X", (0,)))))

    def test_t_squared_equals_s_and_s_squared_equals_z(self):
        self.assertEqual(unitary(circuit(1, ("T", (0,)), ("T", (0,)))),
                         unitary(circuit(1, ("S", (0,)))))
        self.assertEqual(unitary(circuit(1, ("S", (0,)), ("S", (0,)))),
                         unitary(circuit(1, ("Z", (0,)))))
        self.assertEqual(unitary(circuit(1, ("T", (0,)), ("TDG", (0,)))),
                         unitary(circuit(1)))

    def test_controls_have_direction_and_swap_is_not_cnot(self):
        forward = circuit(2, ("CNOT", (0, 1)))
        reverse = circuit(2, ("CNOT", (1, 0)))
        self.assertNotEqual(unitary(forward), unitary(reverse))
        self.assertEqual(entries(evolve(forward, basis_index=1)), [ZERO, ZERO, ZERO, ONE])
        self.assertEqual(entries(evolve(reverse, basis_index=1)), [ZERO, ONE, ZERO, ZERO])
        self.assertEqual(entries(evolve(circuit(2, ("SWAP", (0, 1))), basis_index=1)),
                         [ZERO, ZERO, ONE, ZERO])

    def test_global_phase_is_not_accepted_as_exact_operator_identity(self):
        minus_z = circuit(1, ("X", (0,)), ("Z", (0,)), ("X", (0,)))
        z = circuit(1, ("Z", (0,)))
        self.assertNotEqual(unitary(minus_z), unitary(z))
        self.assertNotEqual(unitary_digest(minus_z), unitary_digest(z))

    def test_deterministic_operator_digest(self):
        bell = circuit(2, ("H", (0,)), ("CNOT", (0, 1)))
        self.assertEqual(unitary_digest(bell), unitary_digest(dict(reversed(list(bell.items())))))
        self.assertEqual(len(unitary_digest(bell)), 64)

    def test_rejects_malformed_bounded_inputs(self):
        bad = [
            {"name": "bad", "qubits": True, "gates": []},
            {"name": "bad", "qubits": 1.0, "gates": []},
            {"name": "bad", "qubits": 5, "gates": []},
            {"name": "bad", "qubits": -1, "gates": []},
            {"name": "bad", "qubits": 2, "gates": [{"gate": "CNOT", "qubits": [0, 0]}]},
            {"name": "bad", "qubits": 2, "gates": [{"gate": "CNOT", "qubits": [0, 2]}]},
            {"name": "bad", "qubits": 1, "gates": [{"gate": "H", "qubits": [True]}]},
            {"name": "bad", "qubits": 1, "gates": [{"gate": "MEASURE", "qubits": [0]}]},
            {"name": "bad", "qubits": 1, "gates": [{"gate": "H", "qubits": [0], "params": []}]},
            {"name": "bad", "qubits": 1, "gates": [{"gate": ["H"], "qubits": [0]}]},
            {"name": "bad", "qubits": 1, "gates": [{"gate": {"H": True}, "qubits": [0]}]},
            {"name": "bad", "qubits": 1, "gates": [{"gate": "CNOT", "qubits": [0]}]},
            {"name": "bad", "qubits": 1, "gates": [] , "verified": True},
            {"name": "bad", "qubits": 1, "gates": [{"gate": "H", "qubits": [0]}] * 65},
            {"name": "", "qubits": 1, "gates": []},
        ]
        for item in bad:
            with self.subTest(item=item), self.assertRaises(CircuitError):
                validate_circuit(item)

    def test_zero_qubit_circuit_is_identity_scalar(self):
        self.assertEqual(entries(evolve(circuit(0))), [ONE])


if __name__ == "__main__":
    unittest.main()
