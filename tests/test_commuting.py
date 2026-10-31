"""Exact commuting receipts must be deterministic, bounded, and untrusted."""
from copy import deepcopy
import hashlib
import json
import unittest
from unittest.mock import patch

from physqed_q import compiler as compiler_module
from physqed_q.compiler import CertificateError, compile_circuit, verify_receipt
from physqed_q.kernel import unitary


def gate(name, *qubits):
    return {"gate": name, "qubits": list(qubits)}


def circuit(gates, qubits=2, name="commutation witness"):
    return {"name": name, "qubits": qubits, "gates": gates}


def rehash(receipt):
    unsigned = {k: v for k, v in receipt.items() if k != "receipt_sha256"}
    receipt["receipt_sha256"] = hashlib.sha256(json.dumps(
        unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False).encode("ascii")).hexdigest()
    return receipt


class CommutingTests(unittest.TestCase):
    def test_disjoint_gate_exposes_inverse_without_changing_legacy(self):
        source = circuit([gate("H", 0), gate("X", 1), gate("H", 0)])
        legacy = compile_circuit(source)
        self.assertEqual(legacy["schema"], "physqed-q-exact-receipt-v1")
        self.assertEqual(legacy["optimized"]["gates"], source["gates"])
        receipt = compile_circuit(source, optimizer="commuting")
        self.assertEqual(receipt["schema"], "physqed-q-exact-receipt-v2")
        self.assertEqual(receipt["optimized"]["gates"], [gate("X", 1)])
        self.assertEqual([s["rule"] for s in receipt["steps"]],
                         ["commute_disjoint", "H_inverse"])
        self.assertEqual(receipt["metrics"], {
            "input": {"gates": 3, "depth": 2, "t_gates": 0, "two_qubit_gates": 0},
            "optimized": {"gates": 1, "depth": 1, "t_gates": 0, "two_qubit_gates": 0},
        })
        self.assertEqual(receipt["metrics"]["input"]["gates"] -
                         receipt["metrics"]["optimized"]["gates"], 2)
        self.assertTrue(verify_receipt(receipt)["verified"])

    def test_overlapping_intervening_gate_blocks_reduction(self):
        source = circuit([gate("H", 0), gate("CNOT", 0, 1), gate("H", 0)])
        receipt = compile_circuit(source, optimizer="commuting")
        self.assertEqual(receipt["optimized"], source)
        self.assertEqual(receipt["steps"], [])
        self.assertTrue(verify_receipt(receipt)["verified"])

    def test_reversed_cnot_does_not_cancel(self):
        source = circuit([gate("CNOT", 0, 1), gate("X", 2),
                          gate("CNOT", 1, 0)], qubits=3)
        receipt = compile_circuit(source, optimizer="commuting")
        self.assertEqual(receipt["optimized"], source)
        self.assertEqual(receipt["steps"], [])

    def test_forged_commutation_rejected_after_rehash(self):
        receipt = compile_circuit(circuit([
            gate("H", 0), gate("X", 1), gate("H", 0)]), optimizer="commuting")
        for key, value in [("rule", "commute_any"), ("index", 0),
                           ("index", True), ("before_sha256", "0" * 64),
                           ("after_sha256", "1" * 64), ("verified", True)]:
            forged = deepcopy(receipt)
            forged["steps"][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(CertificateError):
                verify_receipt(rehash(forged))
        for steps in [receipt["steps"][:1], receipt["steps"] + receipt["steps"]]:
            forged = deepcopy(receipt)
            forged["steps"] = steps
            with self.subTest(steps=steps), self.assertRaises(CertificateError):
                verify_receipt(rehash(forged))

    def test_64_gate_commutation_trace_is_bounded(self):
        # Sixteen nested inverse pairs each cross all 32 disjoint blockers.
        left = [gate(name, 0) for name in ["H", "T"] * 8]
        middle = [gate(name, 1) for name in ["H", "T"] * 16]
        right = [gate(name, 0) for name in ["TDG", "H"] * 8]
        source = circuit(left + middle + right)
        receipt = compile_circuit(source, optimizer="commuting")
        self.assertEqual(len(receipt["steps"]), 528)
        self.assertLessEqual(len(receipt["steps"]), 64 * 64 + 64)
        self.assertEqual(receipt["optimized"]["gates"], middle)
        self.assertEqual(verify_receipt(receipt)["rewrites_checked"], 528)
        forged = deepcopy(receipt)
        forged["steps"] = [receipt["steps"][0]] * (64 * 64 + 65)
        with self.assertRaisesRegex(CertificateError, "unbounded trace"):
            verify_receipt(rehash(forged))
        with patch.object(compiler_module, "MAX_COMMUTING_STEPS", 1):
            with self.assertRaisesRegex(CertificateError, "unbounded trace"):
                compile_circuit(source, optimizer="commuting")

    def test_legacy_receipts_remain_valid_and_scoped(self):
        source = circuit([gate("H", 0), gate("X", 1), gate("H", 0)])
        receipt = compile_circuit(source)
        # Frozen from the pre-v2 adjacent compiler, not derived by this test.
        self.assertEqual(receipt["receipt_sha256"],
                         "7ba08770b0b2f27872f4f141ff05e76b4c54c9f8275707d8331f90eb067b6571")
        self.assertEqual(receipt, compile_circuit(source, optimizer="adjacent"))
        self.assertNotIn("optimizer", receipt["scope"])
        self.assertTrue(verify_receipt(receipt)["verified"])
        modern = compile_circuit(source, optimizer="commuting")
        self.assertEqual(modern["scope"]["optimizer"], "commuting-disjoint-v1")
        for flags in [receipt["scope"], modern["scope"], verify_receipt(modern)]:
            self.assertIs(flags["lean_kernel_verified"], False)
            self.assertIs(flags["hardware_verified"], False)
        with self.assertRaises(TypeError):
            compiler_module.V2_SCOPE["lean_kernel_verified"] = True
        modern["scope"]["optimizer"] = "adjacent"
        with self.assertRaises(CertificateError):
            verify_receipt(rehash(modern))

    def test_adjacent_reductions_precede_lexicographic_commuting_pairs(self):
        source = circuit([gate("H", 0), gate("X", 1), gate("H", 0),
                          gate("T", 1), gate("TDG", 1)])
        receipt = compile_circuit(source, optimizer="commuting")
        self.assertEqual([(s["rule"], s["index"]) for s in receipt["steps"]],
                         [("T_inverse", 3), ("commute_disjoint", 1), ("H_inverse", 0)])
        # The lower i wins even though the pair with i=1 has a lower j.
        source = circuit([gate("H", 0), gate("S", 1), gate("Z", 2),
                          gate("S", 1), gate("H", 0)], qubits=3)
        receipt = compile_circuit(source, optimizer="commuting")
        self.assertEqual([(s["rule"], s["index"]) for s in receipt["steps"]], [
            ("commute_disjoint", 3), ("commute_disjoint", 2),
            ("commute_disjoint", 1), ("H_inverse", 0),
            ("commute_disjoint", 1), ("SS_to_Z", 0)])
        self.assertEqual(receipt, compile_circuit(source, optimizer="commuting"))

    def test_rehashed_endpoint_scope_operator_and_metrics_changes_are_rejected(self):
        receipt = compile_circuit(circuit([
            gate("H", 0), gate("X", 1), gate("H", 0)]), optimizer="commuting")
        for target in ["input", "optimized", "scope", "operator_sha256", "metrics", "extra"]:
            forged = deepcopy(receipt)
            if target in {"input", "optimized"}:
                forged[target]["gates"][0] = gate("Z", 1)
            elif target == "scope":
                forged["scope"]["lean_kernel_verified"] = 0
            elif target == "metrics":
                forged["metrics"]["optimized"]["gates"] = True
            elif target == "extra":
                forged["verified"] = True
            else:
                forged[target] = "0" * 64
            with self.subTest(target=target), self.assertRaises(CertificateError):
                verify_receipt(rehash(forged))

    def test_each_rewrite_and_final_operator_are_exactly_checked(self):
        source = circuit([gate("H", 0), gate("X", 1), gate("H", 0)])
        self.assertEqual(unitary(source), unitary(circuit([gate("X", 1)])))
        original_step = compiler_module._step

        def unsound_step(gates, at, found):
            next_gates, step = original_step(gates, at, found)
            if found[0] == "commute_disjoint":
                # Poison only the intermediate word. Later H cancellation
                # restores the correct endpoint, so a total-only check misses it.
                next_gates[0] = gate("Z", 0)
                step["after_sha256"] = compiler_module._hash(next_gates)
            return next_gates, step

        with patch.object(compiler_module, "_step", side_effect=unsound_step):
            with self.assertRaisesRegex(CertificateError, "not exactly unitary-equivalent"):
                compile_circuit(source, optimizer="commuting")

    def test_empty_and_irreducible_circuits_and_unknown_optimizer(self):
        for source in [circuit([], qubits=0), circuit([gate("T", 0)])]:
            receipt = compile_circuit(source, optimizer="commuting")
            self.assertEqual(receipt["steps"], [])
            self.assertEqual(receipt["optimized"], source)
            self.assertTrue(verify_receipt(receipt)["verified"])
        with self.assertRaisesRegex(CertificateError, "unsupported optimizer"):
            compile_circuit(circuit([]), optimizer="unknown")

    def test_oversized_trace_is_rejected_before_hashing(self):
        receipt = compile_circuit(circuit([
            gate("H", 0), gate("X", 1), gate("H", 0)]), optimizer="commuting")
        receipt["steps"] = [receipt["steps"][0]] * 4161
        with patch.object(compiler_module, "_hash", wraps=compiler_module._hash) as hashing:
            with self.assertRaises(CertificateError):
                verify_receipt(receipt)
            self.assertEqual(hashing.call_count, 0)

    def test_unbounded_nested_fields_are_rejected_before_hashing(self):
        receipt = compile_circuit(circuit([
            gate("H", 0), gate("X", 1), gate("H", 0)]), optimizer="commuting")
        huge = [0] * 10000
        nested = 0
        for _ in range(1500):
            nested = [nested]
        mutations = [
            (("steps", 0, "extra"), huge),
            (("steps", 0, "rule"), nested),
            (("steps", 0, "rule"), "x" * 10000),
            (("steps", 0, "after_sha256"), huge),
            (("steps", 0), {str(i): 0 for i in range(10000)}),
            (("metrics", "input", "gates"), huge),
            (("metrics", "input"), {str(i): 0 for i in range(10000)}),
            (("scope", "kernel"), nested),
            (("scope", "extra"), huge),
            (("input", "gates"), [gate("X", 0)] * 65),
            (("input", "gates", 0, "gate"), "H" * 10000),
            (("input", "gates", 0, "extra"), huge),
            (("optimized", "gates", 0, "qubits"), nested),
            (("optimized", "name"), "x" * 10000),
            (("operator_sha256",), nested),
            (("receipt_sha256",), nested),
        ]
        for path, value in mutations:
            forged = deepcopy(receipt)
            target = forged
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            with self.subTest(path=path), patch.object(
                    compiler_module, "_hash", wraps=compiler_module._hash) as hashing:
                with self.assertRaises(CertificateError):
                    verify_receipt(forged)
                self.assertEqual(hashing.call_count, 0)

    def test_noncanonical_step_scalars_are_rejected_before_hashing(self):
        receipt = compile_circuit(circuit([
            gate("H", 0), gate("X", 1), gate("H", 0)]), optimizer="commuting")
        for key, value in [("index", True), ("index", -1), ("index", 64),
                           ("index", 1.0), ("before_sha256", 0),
                           ("before_sha256", "F" * 64),
                           ("after_sha256", "0" * 65)]:
            forged = deepcopy(receipt)
            forged["steps"][0][key] = value
            with self.subTest(key=key, value=value), patch.object(
                    compiler_module, "_hash", wraps=compiler_module._hash) as hashing:
                with self.assertRaises(CertificateError):
                    verify_receipt(forged)
                self.assertEqual(hashing.call_count, 0)


if __name__ == "__main__":
    unittest.main()
