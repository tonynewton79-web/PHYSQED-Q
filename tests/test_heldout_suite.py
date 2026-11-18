"""Prespecified corpus and refusal contracts; no optional dependencies."""
from collections import Counter
import unittest

from benchmarks.heldout_suite import FAMILIES, generate, manifest
from physqed_q.kernel import validate_circuit


class HeldoutSuiteTests(unittest.TestCase):
    def test_locked_disjoint_seeds_and_families(self):
        dev, test = generate("dev"), generate("heldout")
        self.assertEqual(len(dev), 12)
        self.assertEqual(len(test), 40)
        self.assertEqual(Counter(row["family"] for row in test),
                         {name: 10 for name in FAMILIES})
        self.assertTrue(set(r["name"] for r in dev).isdisjoint(
                        set(r["name"] for r in test)))
        self.assertEqual(generate("heldout"), test)
        self.assertEqual(manifest("heldout"), manifest("heldout"))

    def test_every_circuit_is_within_python_exact_scope(self):
        for split in ("dev", "heldout"):
            for row in generate(split):
                with self.subTest(name=row["name"]):
                    self.assertEqual(
                        validate_circuit(row["circuit"]), row["circuit"])
                    self.assertLessEqual(len(row["circuit"]["gates"]), 64)

    def test_disallows_undeclared_split(self):
        with self.assertRaises(ValueError):
            generate("training2")


if __name__ == "__main__":
    unittest.main()
