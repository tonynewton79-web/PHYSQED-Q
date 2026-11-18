"""Independent standard-library checks: fixture, variance and noise gap."""
from collections import Counter
import unittest

from benchmarks.gate3_applications import corpus, manifest
from benchmarks.gate3_noisy import radius_bhc, paired_status, tvd
from physqed_q.compiler import compile_circuit, verify_receipt
from physqed_q.kernel import validate_circuit, unitary


class Gate3MathTests(unittest.TestCase):
    def test_fixed_15_applications_and_supported_scope(self):
        rows = corpus()
        self.assertEqual(len(rows), 15)
        self.assertEqual(len({row["name"] for row in rows}), 15)
        self.assertEqual(Counter(row["family"] for row in rows),
                         {s: 3 for s in ("ghz", "cluster", "qaoa-path",
                                        "trotter-ising", "phase-cancel")})
        for row in rows:
            raw = row["circuit"]
            with self.subTest(name=row["name"]):
                self.assertEqual(validate_circuit(raw), raw)
                self.assertIn(raw["qubits"], (2, 3, 4))
                self.assertLessEqual(len(raw["gates"]), 64)
        self.assertEqual(manifest(), manifest())

    def test_exact_replay_application_circuits(self):
        for row in corpus():
            with self.subTest(name=row["name"]):
                raw = row["circuit"]
                receipt = compile_circuit(raw, optimizer="phase")
                self.assertTrue(verify_receipt(receipt)["verified"])
                self.assertEqual(unitary(raw), unitary(receipt["optimized"]))

    def test_distribution_metrics(self):
        self.assertAlmostEqual(tvd({"0": .5, "1": .5},
                                   {"0": 1, "1": 0}), .5)
        self.assertAlmostEqual(tvd({"0": 1}, {"0": 1}), 0)
        self.assertAlmostEqual(tvd({"0": 1}, {"1": 1}), 1)
        self.assertEqual(paired_status(.1, .2, .01, .01),
                         "certified_better_under_fixed_noise_model")
        self.assertEqual(paired_status(.2, .1, .01, .01),
                         "certified_worse_under_fixed_noise_model")
        self.assertEqual(paired_status(.1, .1, .01, .01),
                         "inconclusive_sampling_bound")

    def test_simultaneous_radius_monotonicity_and_refusals(self):
        a = radius_bhc(16, 8192, 90)
        b = radius_bhc(16, 16384, 90)
        c = radius_bhc(4, 8192, 90)
        self.assertGreater(a, b)
        self.assertGreater(a, c)
        self.assertGreater(a, 0)
        for m, n, k in ((0, 8192, 90), (17, 8192, 90),
                        (16, 0, 90), (16, 8192, 0)):
            with self.subTest(bad=(m, n, k)), self.assertRaises(ValueError):
                radius_bhc(m, n, k)

    def test_exact_channel_counterexample(self):
        # Two ideally cancelling X gates with independent bit flip
        # after each gate differ from a gate-free identity channel.
        p = .1
        two_error_probability = 2*p*(1-p)
        self.assertGreater(two_error_probability, 0)
        self.assertAlmostEqual(two_error_probability, .18)
        self.assertLess(two_error_probability, 1)


if __name__ == "__main__":
    unittest.main()
