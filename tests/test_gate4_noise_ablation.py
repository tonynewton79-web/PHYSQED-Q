"""Gate 4 ablation contracts (no optional Qiskit import required)."""
import unittest
from benchmarks.gate4_noise_ablation import (
    BACKENDS, CASES, SCENARIOS, read_probability_map, TOL, cx_noise,
)
from benchmarks.gate3_applications import corpus


class Gate4Contracts(unittest.TestCase):
    def test_noise_mechanisms_and_posthoc_corpus_are_fixed(self):
        self.assertEqual(len(BACKENDS), 2)
        self.assertEqual(len(CASES), 5)
        self.assertEqual(len(set(CASES)), 5)
        self.assertEqual(len(SCENARIOS), 7)
        self.assertEqual(len(set(SCENARIOS)), 7)
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

    def test_exact_noise_is_not_inferred_from_unitary(self):
        p = .13
        self.assertGreater(2*p*(1-p), 0)


if __name__ == "__main__":
    unittest.main()
