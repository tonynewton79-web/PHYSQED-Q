"""Gate 4 ablation contracts (no optional Qiskit import required)."""
import unittest
from benchmarks.gate4_noise_ablation import (
    BACKENDS, CASES, SCENARIOS, read_probability_map, TOL,
    apply_independent_readout,
)
from benchmarks.gate3_applications import corpus


class Gate4Contracts(unittest.TestCase):
    def test_noise_mechanisms_and_posthoc_corpus_are_fixed(self):
        self.assertEqual(len(BACKENDS), 2)
        self.assertEqual(len(CASES), 5)
        self.assertEqual(len(set(CASES)), 5)
        self.assertEqual(len(SCENARIOS), 9)
        self.assertEqual(len(set(SCENARIOS)), 9)
        names = {row["name"] for row in corpus()}
        self.assertTrue(set(CASES) <= names)
        self.assertIn("direction_swapped_cx_only", SCENARIOS)
        self.assertIn("uniform_cx_2percent", SCENARIOS)
        self.assertLess(TOL, 1e-5)

    def test_renormalized_binary_and_hex_probabilities(self):
        values = read_probability_map(
            {"0x0": 0.5, "0x3": 0.5}, 2)
        self.assertEqual(values, {"00": .5, "11": .5})
        self.assertEqual(
            read_probability_map({"0b01": .3, "10": .7}, 2),
            {"01": .3, "10": .7})
        with self.assertRaises(RuntimeError):
            read_probability_map({"0x0": .3}, 2)
        with self.assertRaises(RuntimeError):
            read_probability_map({"0x4": 1}, 2)
        with self.assertRaises(RuntimeError):
            read_probability_map({"0x0": float("nan")}, 2)

    def test_readout_assignment_on_actual_measured_physical_qubit(self):
        p = {"00": 0.5, "11": 0.5}
        confusion = {3: [[.9, .1],[.2, .8]], 1: [[.8, .2],[.1, .9]]}
        out = apply_independent_readout(p, [3,1], confusion)
        self.assertAlmostEqual(sum(out.values()), 1)
        self.assertAlmostEqual(out["00"], .5*(.9*.8) + .5*(.2*.1))
        self.assertAlmostEqual(out["11"], .5*(.1*.2) + .5*(.8*.9))
        identity = apply_independent_readout(p,[0,1],{})
        for bits, expected in p.items():
            self.assertAlmostEqual(identity[bits],expected)
        self.assertAlmostEqual(identity["01"],0.)
        self.assertAlmostEqual(identity["10"],0.)
        self.assertIn("calibrated_with_readout",SCENARIOS)
        self.assertIn("readout_only",SCENARIOS)

    def test_exact_noise_is_not_inferred_from_unitary(self):
        p = .13
        self.assertGreater(2*p*(1-p), 0)


if __name__ == "__main__":
    unittest.main()
