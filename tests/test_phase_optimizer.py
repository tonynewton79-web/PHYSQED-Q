"""Adversarial exact tests for opt-in Z-axis phase commutation (v3).

These tests exercise the actual compiler and full-operator receipt replay.
No hardware, T-depth optimality, or external compiler superiority is claimed.
"""
from copy import deepcopy
import hashlib
import json
import os
import random
import unittest

from physqed_q.compiler import (
    CertificateError, compile_circuit, verify_receipt,
)
from physqed_q.kernel import unitary
from physqed_q.lean_certificate import certify_receipt


def gate(kind, *qubits):
    return {"gate": kind, "qubits": list(qubits)}


def circuit(gates, n=2, name="phase test"):
    return {"name": name, "qubits": n, "gates": gates}


def rehash(receipt):
    data = {k: v for k, v in receipt.items() if k != "receipt_sha256"}
    raw = json.dumps(data, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=True, allow_nan=False).encode("ascii")
    receipt["receipt_sha256"] = hashlib.sha256(raw).hexdigest()
    return receipt


class PhaseCommutationTests(unittest.TestCase):
    def test_control_side_cnot_removes_two_t_gates(self):
        raw = circuit([gate("T", 0), gate("CNOT", 0, 1), gate("TDG", 0)])
        old = compile_circuit(raw, optimizer="commuting")
        new = compile_circuit(raw, optimizer="phase")
        self.assertEqual(old["metrics"]["optimized"]["t_gates"], 2)
        self.assertEqual(new["optimized"]["gates"], [gate("CNOT", 0, 1)])
        self.assertEqual(new["metrics"]["optimized"]["t_gates"], 0)
        self.assertEqual(new["schema"], "physqed-q-exact-receipt-v3")
        self.assertEqual(new["scope"]["optimizer"], "phase-commuting-v1")
        self.assertEqual([step["rule"] for step in new["steps"]],
                         ["commute_phase", "T_inverse"])
        self.assertTrue(verify_receipt(new)["verified"])
        self.assertEqual(unitary(raw), unitary(new["optimized"]))

    def test_cz_phase_cancel(self):
        raw = circuit([gate("T", 1), gate("CZ", 0, 1), gate("TDG", 1)])
        new = compile_circuit(raw, optimizer="phase")
        self.assertEqual(new["optimized"]["gates"], [gate("CZ", 0, 1)])
        self.assertTrue(verify_receipt(new)["verified"])

    def test_only_exact_control_commutation_not_target(self):
        raw = circuit([gate("T", 1), gate("CNOT", 0, 1), gate("TDG", 1)])
        new = compile_circuit(raw, optimizer="phase")
        self.assertEqual(new["optimized"]["gates"], raw["gates"])
        self.assertEqual(new["metrics"]["optimized"]["t_gates"], 2)
        self.assertTrue(verify_receipt(new)["verified"])
        self.assertNotEqual(unitary(raw), unitary(circuit([gate("CNOT", 0, 1)])))

    def test_h_and_swap_are_barriers(self):
        for middle in (gate("H", 0), gate("SWAP", 0, 1), gate("X", 0)):
            with self.subTest(middle=middle):
                raw = circuit([gate("T", 0), middle, gate("TDG", 0)])
                new = compile_circuit(raw, optimizer="phase")
                self.assertEqual(new["metrics"]["optimized"]["t_gates"], 2)
                self.assertTrue(verify_receipt(new)["verified"])

    def test_infinite_family_finite_samples(self):
        # T(control) CNOT(control,target)^m TDG(control)
        # always removes two T gates; odd m leaves one CNOT.
        for m in range(1, 20):
            with self.subTest(m=m):
                raw = circuit([gate("T", 0)] +
                              [gate("CNOT", 0, 1)] * m +
                              [gate("TDG", 0)])
                new = compile_circuit(raw, optimizer="phase")
                self.assertEqual(new["metrics"]["optimized"]["t_gates"], 0)
                self.assertEqual(new["optimized"]["gates"],
                                 [gate("CNOT", 0, 1)] if m % 2 else [])
                self.assertTrue(verify_receipt(new)["verified"])

    def test_forged_commutation_label_refused_with_valid_sha(self):
        raw = circuit([gate("T", 0), gate("CNOT", 0, 1), gate("TDG", 0)])
        legitimate = compile_circuit(raw, optimizer="phase")
        forged = deepcopy(legitimate)
        forged["steps"][0]["rule"] = "commute_disjoint"
        rehash(forged)
        with self.assertRaisesRegex(CertificateError, "rewrite trace mismatch"):
            verify_receipt(forged)

    def test_forged_optimiser_scope_refused_with_valid_sha(self):
        raw = circuit([gate("T", 0), gate("CZ", 0, 1), gate("TDG", 0)])
        forged = deepcopy(compile_circuit(raw, optimizer="phase"))
        forged["scope"]["optimizer"] = "commuting-disjoint-v1"
        rehash(forged)
        with self.assertRaisesRegex(CertificateError, "scope/schema"):
            verify_receipt(forged)

    def test_legacy_v2_receipt_unchanged(self):
        raw = circuit([gate("H", 0), gate("X", 1), gate("H", 0)])
        receipt = compile_circuit(raw, optimizer="commuting")
        self.assertEqual(receipt["schema"], "physqed-q-exact-receipt-v2")
        self.assertEqual(receipt["optimized"]["gates"], [gate("X", 1)])
        self.assertTrue(verify_receipt(receipt)["verified"])

    def test_random_exact_equivalence_and_t_monotonicity(self):
        rng = random.Random(20261118)
        single = ("H", "X", "Z", "S", "SDG", "T", "TDG")
        for n in range(1, 5):
            for case in range(8):
                gates = []
                for _ in range(5 + (case % 5)):
                    if n > 1 and rng.randrange(4) == 0:
                        a, b = rng.sample(range(n), 2)
                        gates.append(gate(rng.choice(("CNOT", "CZ", "SWAP")), a, b))
                    else:
                        gates.append(gate(rng.choice(single), rng.randrange(n)))
                raw = circuit(gates, n, f"random {n} {case}")
                new = compile_circuit(raw, optimizer="phase")
                self.assertTrue(verify_receipt(new)["verified"])
                self.assertEqual(unitary(raw), unitary(new["optimized"]))
                self.assertLessEqual(new["metrics"]["optimized"]["gates"], len(gates))
                old_t = sum(g["gate"] in ("T", "TDG") for g in gates)
                self.assertLessEqual(new["metrics"]["optimized"]["t_gates"], old_t)

    @unittest.skipUnless(os.environ.get("PHYSQED_Q_LEAN_BIN"),
                         "real Lean 4.24.0 required; Python replay still tested")
    def test_real_lean_checks_phase_output(self):
        raw = circuit([gate("T", 0), gate("CNOT", 0, 1), gate("TDG", 0)])
        receipt = compile_circuit(raw, optimizer="phase")
        report = certify_receipt(
            receipt, lean_executable=os.environ["PHYSQED_Q_LEAN_BIN"])
        self.assertIs(report["lean_theorem_checked"], True)
        self.assertIs(report["lean_gate_decoder_checked"], True)
        self.assertIs(report["python_compiler_end_to_end_formalized"], False)


if __name__ == "__main__":
    unittest.main()
