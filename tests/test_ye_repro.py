"""Independent-facing PHYSQED-Q two-qubit acceptance/refusal demonstration.

Run: python -m unittest discover -s tests -p 'test_ye_repro.py' -v
For actual Lean integration set PHYSQED_Q_LEAN_BIN to a Lean 4.24.0 binary.
This exercises the repository's real compiler, replay checker and Lean bridge.
"""
from copy import deepcopy
import hashlib
import json
import os
import unittest

from physqed_q.compiler import CertificateError, compile_circuit, metrics, verify_receipt
from physqed_q.kernel import CircuitError, unitary
from physqed_q.lean_certificate import (
    LeanBridgeError, _run_source, certify_receipt, render_receipt_theorem,
)


def gate(label, *qubits):
    return {"gate": label, "qubits": list(qubits)}


VALID = {
    "name": "Ye correspondence: two-qubit exact witness",
    "qubits": 2,
    "gates": [
        gate("H", 0), gate("Z", 0), gate("H", 0),
        gate("CNOT", 0, 1), gate("CNOT", 0, 1),
        gate("T", 0), gate("T", 0),
    ],
}


def canonical_digest(document):
    """The public, non-authenticating receipt hash format."""
    canonical = json.dumps(document, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=True, allow_nan=False).encode("ascii")
    return hashlib.sha256(canonical).hexdigest()


class YeTwoQubitRepro(unittest.TestCase):
    def test_01_valid_rewrite_and_exact_replay(self):
        receipt = compile_circuit(VALID)
        self.assertEqual(receipt["optimized"]["gates"],
                         [gate("X", 0), gate("S", 0)])
        self.assertEqual([step["rule"] for step in receipt["steps"]],
                         ["HZH_to_X", "CNOT_inverse", "TT_to_S"])
        self.assertEqual(receipt["metrics"]["input"]["gates"], 7)
        self.assertEqual(receipt["metrics"]["optimized"]["gates"], 2)
        self.assertEqual(receipt["metrics"]["input"]["t_gates"], 2)
        self.assertEqual(receipt["metrics"]["optimized"]["t_gates"], 0)
        self.assertEqual(unitary(VALID), unitary(receipt["optimized"]))
        result = verify_receipt(receipt)
        self.assertEqual(result["rewrites_checked"], 3)
        self.assertIs(result["verified"], True)
        self.assertIs(result["lean_kernel_verified"], False)
        self.assertIs(result["hardware_verified"], False)

    def test_02_wrong_rewrite_rejected_even_after_rehash(self):
        receipt = compile_circuit(VALID)
        forged = deepcopy(receipt)
        # Deliberately false: H Z H is X, not Z.
        forged["optimized"]["gates"] = [gate("Z", 0), gate("S", 0)]
        # Repair apparent metadata, including the public checksum, so failure
        # cannot be attributed simply to a stale SHA-256 digest.
        forged["metrics"]["optimized"] = metrics(forged["optimized"])
        forged["receipt_sha256"] = canonical_digest({
            key: val for key, val in forged.items() if key != "receipt_sha256"
        })
        self.assertNotEqual(unitary(VALID), unitary(forged["optimized"]))
        with self.assertRaisesRegex(CertificateError, "output differs from trace"):
            verify_receipt(forged)

    def test_03_unsupported_arbitrary_rotation_refused(self):
        unsupported = {
            "name": "Unsupported RZ(theta) request",
            "qubits": 2,
            "gates": [gate("RZ", 0)],
        }
        with self.assertRaisesRegex(CircuitError, "gate 0 unsupported"):
            compile_circuit(unsupported)

    def test_04_three_qubit_python_scope_not_lean_scope(self):
        three = {"name": "Three-qubit GHZ", "qubits": 3,
                 "gates": [gate("H", 0), gate("CNOT", 0, 1),
                           gate("CNOT", 1, 2)]}
        receipt = compile_circuit(three)
        self.assertIs(verify_receipt(receipt)["verified"], True)
        with self.assertRaisesRegex(LeanBridgeError, "exactly two qubits"):
            render_receipt_theorem(receipt)

    @unittest.skipUnless(os.environ.get("PHYSQED_Q_LEAN_BIN"),
                         "Lean 4.24.0 not configured; Python tests still run")
    def test_05_real_lean_accepts_two_qubit_theorem(self):
        report = certify_receipt(
            compile_circuit(VALID),
            lean_executable=os.environ["PHYSQED_Q_LEAN_BIN"],
        )
        self.assertIs(report["lean_theorem_checked"], True)
        self.assertIs(report["lean_gate_decoder_checked"], True)
        self.assertIs(report["python_compiler_end_to_end_formalized"], False)

    @unittest.skipUnless(os.environ.get("PHYSQED_Q_LEAN_BIN"),
                         "Lean 4.24.0 not configured; Python tests still run")
    def test_06_real_lean_refuses_wrong_or_unsupported_gate_data(self):
        rendered = render_receipt_theorem(compile_circuit(VALID))
        good = '[("X", [0]), ("S", [0])]'
        self.assertIn(good, rendered)
        bad_operator = rendered.replace(good, '[("Z", [0]), ("S", [0])]')
        bad_gate = rendered.replace('("H", [0])', '("RZ", [0])', 1)
        for label, mutated in (("incorrect operator", bad_operator),
                               ("unsupported Lean gate", bad_gate)):
            with self.subTest(label=label), self.assertRaises(LeanBridgeError):
                _run_source(mutated, lean_executable=os.environ["PHYSQED_Q_LEAN_BIN"])


if __name__ == "__main__":
    unittest.main()
