"""Internal corpus reports measured resources and replayable exact results."""

import json
from pathlib import Path
import subprocess
import sys
import unittest

from benchmarks.commuting_suite import run_suite
from physqed_q.compiler import compile_circuit, verify_receipt
from physqed_q.kernel import unitary


ROOT = Path(__file__).resolve().parents[1]


class CommutingBenchmarkTests(unittest.TestCase):
    def test_disjoint_fixture_improves_three_gates_to_one(self):
        case = run_suite()["cases"][0]
        with (ROOT / "examples" / "commuting.json").open() as stream:
            self.assertEqual(case["input"], json.load(stream))
        self.assertEqual(case["input"]["gates"], [
            {"gate": "H", "qubits": [0]},
            {"gate": "X", "qubits": [1]},
            {"gate": "H", "qubits": [0]},
        ])
        self.assertEqual(case["v1"]["metrics"], {
            "gates": 3, "depth": 2, "t_gates": 0, "two_qubit_gates": 0})
        self.assertEqual(case["v2"]["metrics"], {
            "gates": 1, "depth": 1, "t_gates": 0, "two_qubit_gates": 0})
        self.assertEqual(case["v2_minus_v1"], {
            "gates": -2, "depth": -1, "t_gates": 0, "two_qubit_gates": 0})

    def test_every_case_replays_both_receipts_and_matches_reported_output(self):
        cases = run_suite()["cases"]
        self.assertEqual([case["id"] for case in cases], [
            "disjoint_inverse", "adjacent_parity", "blocked_overlap"])
        for case in cases:
            for version, optimizer in [("v1", "adjacent"), ("v2", "commuting")]:
                with self.subTest(case=case["id"], version=version):
                    receipt = compile_circuit(case["input"], optimizer=optimizer)
                    self.assertTrue(verify_receipt(receipt)["verified"])
                    self.assertIs(case[version]["exact_operator_verified"], True)
                    self.assertEqual(case[version]["receipt_sha256"],
                                     receipt["receipt_sha256"])
                    self.assertEqual(case[version]["metrics"],
                                     receipt["metrics"]["optimized"])
                    self.assertEqual(case[version]["optimized"], receipt["optimized"])
                    self.assertEqual(unitary(case["input"]),
                                     unitary(case[version]["optimized"]))
        parity, blocked = cases[1:]
        for version in ["v1", "v2"]:
            self.assertEqual(parity[version]["metrics"]["gates"], 1)
            self.assertEqual(parity[version]["metrics"]["t_gates"], 0)
            self.assertEqual(blocked[version]["metrics"]["gates"], 3)
            self.assertEqual(blocked[version]["optimized"], blocked["input"])
        self.assertEqual(parity["v2_minus_v1"]["gates"], 0)
        self.assertEqual(blocked["v2_minus_v1"]["gates"], 0)

    def test_cli_emits_byte_identical_json_in_separate_processes(self):
        command = [sys.executable, "-m", "benchmarks.commuting_suite"]
        first = subprocess.check_output(command, cwd=ROOT)
        second = subprocess.check_output(command, cwd=ROOT)
        self.assertEqual(first, second)
        self.assertEqual(json.loads(first), run_suite())


if __name__ == "__main__":
    unittest.main()
