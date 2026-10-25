"""Fail-closed receipt-specific Lean certificate bridge contract."""

import json
import os
import unittest

from physqed_q.compiler import compile_circuit
from physqed_q.lean_certificate import (
    LeanBridgeError, certify_receipt, render_receipt_theorem, _run_source,
)


EXAMPLE = {
    "name": "receipt witness",
    "qubits": 2,
    "gates": [
        {"gate": "H", "qubits": [0]},
        {"gate": "Z", "qubits": [0]},
        {"gate": "H", "qubits": [0]},
        {"gate": "CNOT", "qubits": [0, 1]},
        {"gate": "CNOT", "qubits": [0, 1]},
        {"gate": "T", "qubits": [0]},
        {"gate": "T", "qubits": [0]},
    ],
}


class GeneratedLeanTests(unittest.TestCase):
    def setUp(self):
        self.receipt = compile_circuit(EXAMPLE)

    def test_render_is_deterministic_and_binds_actual_gate_words(self):
        source = render_receipt_theorem(self.receipt)
        self.assertEqual(source, render_receipt_theorem(self.receipt))
        self.assertIn('[("H", [0]), ("Z", [0]), ("H", [0]),', source)
        self.assertIn('("CNOT", [0, 1]), ("CNOT", [0, 1]),', source)
        self.assertIn('[("X", [0]), ("S", [0])]', source)
        self.assertIn("rawOperatorEq receiptInput receiptOutput", source)
        self.assertIn("import RawGateBridge", source)
        self.assertNotIn(".cnot01", source)
        self.assertNotIn("sorry", source)
        self.assertNotIn("axiom ", source)

    def test_control_target_reversal_stays_as_raw_gate_data(self):
        reverse = {"name": "reverse", "qubits": 2,
                   "gates": [{"gate": "CNOT", "qubits": [1, 0]},
                             {"gate": "CNOT", "qubits": [1, 0]}]}
        self.assertIn('[("CNOT", [1, 0]), ("CNOT", [1, 0])]',
                      render_receipt_theorem(compile_circuit(reverse)))

    def test_malicious_name_never_enters_lean_source(self):
        raw = {**EXAMPLE, "name": "attack\n#eval IO.println \"owned\""}
        source = render_receipt_theorem(compile_circuit(raw))
        self.assertNotIn("owned", source)

    def test_tampered_receipt_rejected_before_render(self):
        altered = json.loads(json.dumps(self.receipt))
        altered["optimized"]["gates"][0]["gate"] = "Z"
        with self.assertRaises(LeanBridgeError):
            render_receipt_theorem(altered)

    def test_rejects_non_two_qubit_and_oversize_lean_scope(self):
        single = {"name": "single", "qubits": 1,
                  "gates": [{"gate": "H", "qubits": [0]}]}
        with self.assertRaisesRegex(LeanBridgeError, "two qubits"):
            render_receipt_theorem(compile_circuit(single))
        oversized = {"name": "oversize", "qubits": 2,
                     "gates": [{"gate": "X", "qubits": [0]}] * 17}
        with self.assertRaisesRegex(LeanBridgeError, "sixteen"):
            render_receipt_theorem(compile_circuit(oversized))

    def test_missing_lean_is_not_reported_as_verified(self):
        with self.assertRaises(LeanBridgeError):
            certify_receipt(self.receipt, lean_executable="/no/such/lean")


@unittest.skipUnless(os.environ.get("PHYSQED_Q_LEAN_BIN"),
                     "actual Lean binary not configured")
class CompiledLeanTests(unittest.TestCase):
    def test_real_lean_accepts_correct_operator_certificate(self):
        receipt = compile_circuit(EXAMPLE)
        report = certify_receipt(receipt,
                                 lean_executable=os.environ["PHYSQED_Q_LEAN_BIN"])
        self.assertTrue(report["lean_theorem_checked"])
        self.assertTrue(report["lean_gate_decoder_checked"])
        self.assertIn("RawGateBridge.lean", report["formal_source_sha256"])
        self.assertFalse(report["python_compiler_end_to_end_formalized"])
        self.assertEqual(report["receipt_sha256"], receipt["receipt_sha256"])

    def test_real_lean_rejects_false_target_operator(self):
        receipt = compile_circuit(EXAMPLE)
        source = render_receipt_theorem(receipt).replace(
            '[("X", [0]), ("S", [0])]', '[("Z", [0]), ("S", [0])]'
        )
        with self.assertRaises(LeanBridgeError):
            _run_source(source, lean_executable=os.environ["PHYSQED_Q_LEAN_BIN"])

    def test_real_lean_rejects_invalid_raw_gate_not_silently_skipped(self):
        source = render_receipt_theorem(compile_circuit(EXAMPLE))
        for wrong in ('("INVALID", [0])', '("H", [0, 1])', '("H", [2])'):
            with self.subTest(wrong=wrong):
                altered = source.replace('("H", [0])', wrong, 1)
                with self.assertRaises(LeanBridgeError):
                    _run_source(altered,
                                lean_executable=os.environ["PHYSQED_Q_LEAN_BIN"])

    def test_real_lean_rejects_invalid_optimized_gate(self):
        source = render_receipt_theorem(compile_circuit(EXAMPLE))
        altered = source.replace('("S", [0])', '("S", [2])')
        with self.assertRaises(LeanBridgeError):
            _run_source(altered, lean_executable=os.environ["PHYSQED_Q_LEAN_BIN"])

    def test_all_ten_supported_gates_have_exact_two_qubit_semantics(self):
        patterns = [
            ("H", [1], "H", [1]),
            ("X", [0], "X", [0]),
            ("Z", [1], "Z", [1]),
            ("S", [0], "SDG", [0]),
            ("T", [1], "TDG", [1]),
            ("CNOT", [1, 0], "CNOT", [1, 0]),
            ("CZ", [1, 0], "CZ", [1, 0]),
            ("SWAP", [0, 1], "SWAP", [0, 1]),
        ]
        gates = []
        for left, lq, right, rq in patterns:
            gates.extend(({"gate": left, "qubits": lq},
                          {"gate": right, "qubits": rq}))
        receipt = compile_circuit({"name": "all gates", "qubits": 2, "gates": gates})
        self.assertEqual(receipt["optimized"]["gates"], [])
        report = certify_receipt(receipt,
                                 lean_executable=os.environ["PHYSQED_Q_LEAN_BIN"])
        self.assertTrue(report["lean_theorem_checked"])


if __name__ == "__main__":
    unittest.main()
