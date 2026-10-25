"""Certificate adversarial tests: no self-asserted verification is trusted."""
from copy import deepcopy
import hashlib
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from physqed_q import compiler as compiler_module
from physqed_q.compiler import CertificateError, compile_circuit, metrics, verify_receipt


def gate(name, *qubits):
    return {"gate": name, "qubits": list(qubits)}


SOURCE = {"name": "optimizer witness", "qubits": 2, "gates": [
    gate("H", 0), gate("Z", 0), gate("H", 0),
    gate("CNOT", 0, 1), gate("CNOT", 0, 1),
    gate("T", 0), gate("T", 0),
]}


class CompilerTests(unittest.TestCase):
    def test_compiler_rewrites_three_exact_identities(self):
        receipt = compile_circuit(SOURCE)
        self.assertEqual(receipt["optimized"]["gates"], [gate("X", 0), gate("S", 0)])
        self.assertEqual([s["rule"] for s in receipt["steps"]],
                         ["HZH_to_X", "CNOT_inverse", "TT_to_S"])
        self.assertEqual(receipt["metrics"]["input"]["gates"], 7)
        self.assertEqual(receipt["metrics"]["optimized"]["gates"], 2)
        self.assertEqual(receipt["metrics"]["input"]["t_gates"], 2)
        self.assertEqual(receipt["metrics"]["optimized"]["t_gates"], 0)
        self.assertTrue(verify_receipt(receipt)["verified"])

    def test_changed_output_is_rejected_even_with_rehashed_integrity(self):
        receipt = compile_circuit(SOURCE)
        fake = deepcopy(receipt)
        fake["optimized"]["gates"] = [gate("Z", 0), gate("S", 0)]
        unsigned = {k: v for k, v in fake.items() if k != "receipt_sha256"}
        fake["receipt_sha256"] = hashlib.sha256(json.dumps(
            unsigned, sort_keys=True, separators=(",", ":"),
            ensure_ascii=True, allow_nan=False).encode("ascii")).hexdigest()
        # A freshly recomputed digest cannot turn a wrong circuit into evidence.
        with self.assertRaises(CertificateError):
            verify_receipt(fake)

    def test_unsound_rewrite_rule_is_caught_by_exact_semantics(self):
        source = {"name": "mutation witness", "qubits": 1, "gates": [gate("H", 0)]}

        def unsound_rule(gates, index):
            if gates[index]["gate"] == "H":
                return ("forged_H_to_Z", 1, [gate("Z", 0)])
            return None

        with patch.object(compiler_module, "_replacement", side_effect=unsound_rule):
            with self.assertRaisesRegex(CertificateError, "not exactly unitary-equivalent"):
                compile_circuit(source)

    def test_all_certificate_mutations_are_rejected(self):
        original = compile_circuit(SOURCE)
        examples = []
        a = deepcopy(original)
        a["input"]["gates"][0] = gate("X", 0)
        examples.append(a)
        b = deepcopy(original)
        b["optimized"]["gates"].append(gate("Z", 0))
        examples.append(b)
        c = deepcopy(original)
        c["steps"][1]["rule"] = "T_inverse"
        examples.append(c)
        d = deepcopy(original)
        d["metrics"]["optimized"]["depth"] += 1
        examples.append(d)
        e = deepcopy(original)
        e["operator_sha256"] = "0" * 64
        examples.append(e)
        f = deepcopy(original)
        f["receipt_sha256"] = "1" * 64
        examples.append(f)
        g = deepcopy(original)
        g["scope"]["lean_kernel_verified"] = True
        examples.append(g)
        h = deepcopy(original)
        h["verified"] = True
        examples.append(h)
        for counterexample in examples:
            with self.subTest(mutated=counterexample), self.assertRaises(CertificateError):
                verify_receipt(counterexample)

    def test_inverse_and_phase_rules_replay(self):
        circuit = {"name": "rules", "qubits": 2, "gates": [
            gate("S", 0), gate("SDG", 0),
            gate("T", 1), gate("TDG", 1),
            gate("CZ", 0, 1), gate("CZ", 0, 1),
            gate("SWAP", 0, 1), gate("SWAP", 0, 1),
            gate("H", 1), gate("X", 1), gate("H", 1),
        ]}
        receipt = compile_circuit(circuit)
        self.assertEqual(receipt["optimized"]["gates"], [gate("Z", 1)])
        self.assertTrue(verify_receipt(receipt)["verified"])

    def test_metric_depth_parallelism(self):
        c = {"name": "parallel", "qubits": 3, "gates": [
            gate("H", 0), gate("H", 1), gate("CNOT", 0, 2)
        ]}
        self.assertEqual(metrics(c), {"gates": 3, "depth": 2, "t_gates": 0, "two_qubit_gates": 1})

    def test_identity_and_unchanged_circuits_still_get_receipts(self):
        for c in [
            {"name": "empty", "qubits": 0, "gates": []},
            {"name": "bell", "qubits": 2, "gates": [gate("H", 0), gate("CNOT", 0, 1)]},
        ]:
            with self.subTest(circuit=c["name"]):
                receipt = compile_circuit(c)
                self.assertEqual(receipt["steps"], [])
                self.assertTrue(verify_receipt(receipt)["verified"])
                self.assertFalse(receipt["scope"]["hardware_verified"])
                self.assertFalse(receipt["scope"]["lean_kernel_verified"])

    def test_tampered_step_position_fails_even_if_result_were_equal(self):
        receipt = compile_circuit(SOURCE)
        forged = deepcopy(receipt)
        forged["steps"][0]["index"] = 1
        with self.assertRaises(CertificateError):
            verify_receipt(forged)

    def test_rehashed_type_confusion_must_not_certify(self):
        receipt = compile_circuit(SOURCE)
        for target, key, changed in [
            ("metrics", "gates", False),
            ("steps", "index", False),
            ("scope", "lean_kernel_verified", 0),
            ("scope", "integrity_not_authenticity", 1.0),
        ]:
            forged = deepcopy(receipt)
            if target == "metrics":
                forged["metrics"]["input"][key] = changed
            elif target == "steps":
                forged["steps"][0][key] = changed
            else:
                forged["scope"][key] = changed
            unsigned = {k: v for k, v in forged.items() if k != "receipt_sha256"}
            forged["receipt_sha256"] = hashlib.sha256(json.dumps(
                unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                allow_nan=False).encode("ascii")).hexdigest()
            with self.subTest(target=target, key=key), self.assertRaises(CertificateError):
                verify_receipt(forged)


if __name__ == "__main__":
    unittest.main()
