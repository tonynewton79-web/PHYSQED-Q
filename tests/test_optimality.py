"""Bounded optimality claims are exact, exhaustive, and untrusted."""
from copy import deepcopy
import hashlib
import json
import unittest
from unittest.mock import patch

from physqed_q import kernel, optimality
from physqed_q.optimality import OptimalityError, certify_optimality, verify_optimality


def circuit(word, name="optimality witness"):
    return {"name": name, "qubits": 1,
            "gates": [{"gate": kind, "qubits": [0]} for kind in word]}


def rehash(receipt):
    unsigned = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    receipt["receipt_sha256"] = hashlib.sha256(json.dumps(
        unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False).encode("ascii")).hexdigest()
    return receipt


class OptimalityTests(unittest.TestCase):
    def test_hxh_shortest_single_gate(self):
        receipt = certify_optimality(circuit(["H", "X", "H"]))
        self.assertEqual(receipt["schema"], "physqed-q-bounded-optimality-v1")
        self.assertEqual(receipt["optimized"], circuit(["Z"]))
        self.assertEqual(receipt["search"]["minimum_gates"], 1)
        self.assertEqual(receipt["search"]["words_examined"], 19608)
        self.assertTrue(verify_optimality(receipt)["verified"])

    def test_identity_zero_gates(self):
        receipt = certify_optimality(circuit(["H", "H"]))
        self.assertEqual(receipt["optimized"], circuit([]))
        self.assertEqual(receipt["search"]["minimum_gates"], 0)
        self.assertEqual(receipt["search"]["words_examined"], 19608)
        self.assertTrue(verify_optimality(receipt)["verified"])

    def test_rehashed_nonminimal_winner_rejected(self):
        receipt = certify_optimality(circuit(["H", "H"]), horizon=2)
        receipt["optimized"] = circuit(["H", "H"])
        receipt["search"]["minimum_gates"] = 2
        with self.assertRaises(OptimalityError):
            verify_optimality(rehash(receipt))

    def test_global_phase_not_quotiented(self):
        # X Z X Z is -I, not I. No <=3-gate representative exists.
        with self.assertRaises(OptimalityError):
            certify_optimality(circuit(["X", "Z", "X", "Z"]), horizon=3)
        receipt = certify_optimality(circuit([]), horizon=0)
        receipt["input"] = circuit(["X", "Z", "X", "Z"])
        receipt["operator_sha256"] = kernel.unitary_digest(receipt["input"])
        with self.assertRaises(OptimalityError):
            verify_optimality(rehash(receipt))

    def test_horizon_edges(self):
        receipt = certify_optimality(circuit(["H", "H"]), horizon=0)
        self.assertEqual(receipt["search"]["words_examined"], 1)
        self.assertTrue(verify_optimality(receipt)["verified"])
        with self.assertRaises(OptimalityError):
            certify_optimality(circuit(["T"]), horizon=0)
        for bound in [True, False, 1.0, -1, 6, "2", None]:
            # Invalid bounds must be rejected before any expensive planner call.
            with self.subTest(bound=bound), patch.object(
                    optimality, "_planner_search", side_effect=AssertionError("planner reached")):
                with self.assertRaises(OptimalityError):
                    certify_optimality(circuit([]), horizon=bound)

    def test_unrepresentable_operator_fails_closed(self):
        with self.assertRaises(OptimalityError):
            certify_optimality(circuit(["H", "T"]), horizon=1)

    def test_checker_independent_of_planner(self):
        receipt = certify_optimality(circuit(["H", "X"]), horizon=2)
        with patch.object(optimality, "_planner_search", side_effect=AssertionError("planner used")):
            self.assertTrue(verify_optimality(receipt)["verified"])
        with patch.object(optimality, "_planner_search", return_value=((2, 0, (0, 0)), 57)):
            with self.assertRaises(OptimalityError):
                certify_optimality(circuit([]), horizon=2)

    def test_complete_enumeration_even_on_identity(self):
        receipt = certify_optimality(circuit([]))
        with patch.object(kernel, "_apply", wraps=kernel._apply) as apply_gate:
            checked = verify_optimality(receipt)
        self.assertEqual(checked["words_examined"], 19608)
        # Every nonempty node applies one gate to both basis columns.
        self.assertEqual(apply_gate.call_count, 39214)

    def test_t_count_breaks_equal_length_ties(self):
        # Both are shortest length 4; H TDG X T has two T gates.
        source = circuit(["H", "TDG", "X", "T"])
        self.assertEqual(kernel.unitary(source), kernel.unitary(circuit(["S", "H", "SDG", "H"])))
        receipt = certify_optimality(source, horizon=4)
        self.assertEqual(receipt["search"]["minimum_gates"], 4)
        self.assertEqual(receipt["search"]["t_gates"], 0)
        forged = deepcopy(receipt)
        forged["optimized"] = source
        forged["search"]["t_gates"] = 2
        with self.assertRaises(OptimalityError):
            verify_optimality(rehash(forged))

    def test_fixed_alphabet_breaks_equal_cost_ties(self):
        receipt = certify_optimality(circuit(["Z", "H"]), horizon=2)
        self.assertEqual(receipt["optimized"], circuit(["H", "X"]))
        receipt["optimized"] = circuit(["Z", "H"])
        with self.assertRaises(OptimalityError):
            verify_optimality(rehash(receipt))

    def test_search_scope_digest_and_context_are_untrusted(self):
        receipt = certify_optimality(circuit(["T"]), horizon=1)
        changes = [
            (("schema",), "physqed-q-exact-receipt-v1"),
            (("search", "words_examined"), 1),
            (("search", "minimum_gates"), 0),
            (("search", "t_gates"), 0),
            (("search", "alphabet"), ["T", "H", "X", "Z", "S", "SDG", "TDG"]),
            (("search", "objective"), ["t_gates", "total_gates", "alphabet_lexicographic"]),
            (("scope", "hardware_verified"), True),
            (("scope", "lean_kernel_verified"), 0),
            (("operator_sha256",), "0" * 64),
            (("optimized", "name"), "other context"),
            (("optimized", "qubits"), 2),
        ]
        for path, value in changes:
            forged = deepcopy(receipt)
            target = forged
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            with self.subTest(path=path), self.assertRaises(OptimalityError):
                verify_optimality(rehash(forged))

    def test_unbounded_receipt_rejected_before_hashing(self):
        receipt = certify_optimality(circuit(["T"]), horizon=1)
        nested = 0
        for _ in range(1500):
            nested = [nested]
        huge = [0] * 10000
        changes = [
            (("extra",), huge), (("schema",), nested),
            (("search",), {str(i): 0 for i in range(10000)}),
            (("search", "horizon"), 6), (("search", "alphabet"), huge),
            (("search", "objective"), nested), (("search", "words_examined"), nested),
            (("search", "minimum_gates"), True), (("search", "t_gates"), 1.0),
            (("scope", "claim"), nested), (("scope", "extra"), huge),
            (("input", "name"), "x" * 121), (("input", "qubits"), True),
            (("input", "gates"), [{"gate": "X", "qubits": [0]}] * 65),
            (("input", "gates", 0, "gate"), "T" * 10000),
            (("input", "gates", 0, "qubits"), nested),
            (("input", "gates", 0, "extra"), huge),
            (("optimized", "gates"), circuit(["T", "T"])["gates"]),
            (("operator_sha256",), nested), (("receipt_sha256",), nested),
        ]
        for path, value in changes:
            forged = deepcopy(receipt)
            target = forged
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            with self.subTest(path=path), patch.object(
                    optimality, "_hash", side_effect=AssertionError("hash reached")):
                with self.assertRaises(OptimalityError):
                    verify_optimality(forged)

    def test_strict_builtin_json_types_and_input_bounds(self):
        class DictSubclass(dict):
            pass

        class ListSubclass(list):
            pass

        class StringSubclass(str):
            pass

        receipt = certify_optimality(circuit([]), horizon=0)
        for bad in [DictSubclass(receipt), None, []]:
            with self.subTest(bad=type(bad)), self.assertRaises(OptimalityError):
                verify_optimality(bad)
        for path, value in [(("input", "gates"), ListSubclass()),
                            (("input", "name"), StringSubclass("witness"))]:
            forged = deepcopy(receipt)
            forged[path[0]][path[1]] = value
            with self.subTest(path=path), self.assertRaises(OptimalityError):
                verify_optimality(forged)
        for source in [circuit(["H"] * 65), {**circuit([]), "qubits": 0},
                       {**circuit([]), "qubits": 2}, {**circuit([]), "name": ""}]:
            with self.subTest(source=source), self.assertRaises(OptimalityError):
                certify_optimality(source, horizon=0)
        source = circuit(["H"] * 64, name="preserved name")
        result = certify_optimality(source, horizon=0)
        self.assertEqual(result["optimized"], circuit([], name="preserved name"))

    def test_determinism_and_integrity(self):
        source = circuit(["H", "X", "H"])
        receipt = certify_optimality(source, horizon=1)
        self.assertEqual(receipt, certify_optimality(source, horizon=1))
        self.assertEqual(receipt["search"]["objective"],
                         ["total_gates", "t_gates", "alphabet_lexicographic"])
        self.assertEqual(receipt["scope"], {
            "claim": "bounded exact one-qubit gate-count minimum",
            "lean_kernel_verified": False, "hardware_verified": False,
            "quantum_advantage_demonstrated": False, "integrity_not_authenticity": True})
        receipt["receipt_sha256"] = "0" * 64
        with self.assertRaises(OptimalityError):
            verify_optimality(receipt)


if __name__ == "__main__":
    unittest.main()
