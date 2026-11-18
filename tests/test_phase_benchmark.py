"""Verify reproducibility of bounded phase-ablation metrics."""
import unittest

from benchmarks.phase_suite import run


class PhaseBenchmarkTests(unittest.TestCase):
    def test_case_count_replay_and_nonincrease(self):
        report = run()
        self.assertEqual(len(report["cases"]), 6)
        self.assertIs(report["external_ranking"], False)
        for case in report["cases"]:
            for policy in ("adjacent", "commuting", "phase"):
                self.assertTrue(case["policies"][policy]["replayed"])
            self.assertLessEqual(case["policies"]["phase"]["t_gates"],
                                 case["policies"]["commuting"]["t_gates"])

    def test_control_witness_and_target_negative(self):
        case = {entry["case"]: entry for entry in run()["cases"]}
        self.assertEqual(case["control-CNOT"]["policies"]["commuting"]["t_gates"], 2)
        self.assertEqual(case["control-CNOT"]["policies"]["phase"]["t_gates"], 0)
        self.assertEqual(case["target-CNOT-negative"]["policies"]["phase"]["t_gates"], 2)
        self.assertEqual(case["CZ-diagonal"]["policies"]["phase"]["t_gates"], 0)
        self.assertEqual(case["H-barrier-negative"]["policies"]["phase"]["t_gates"], 2)


if __name__ == "__main__":
    unittest.main()
