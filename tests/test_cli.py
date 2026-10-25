"""End-to-end CLI validation; subprocesses use the actual executable module."""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


PROJECT = Path(__file__).resolve().parents[1]
PACKAGE_PARENT = str(PROJECT)


def invoke(*args):
    env = dict(os.environ, PYTHONPATH=PACKAGE_PARENT)
    return subprocess.run([sys.executable, "-m", "physqed_q", *map(str, args)],
                          cwd=PROJECT, env=env, text=True, capture_output=True,
                          timeout=20, check=False)


class CommandLineTests(unittest.TestCase):
    def test_compiles_receipt_and_replays_it_from_file(self):
        source = PROJECT / "examples" / "optimize.json"
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "receipt.json"
            made = invoke("compile", source, "--output", target)
            self.assertEqual(made.returncode, 0, made.stderr)
            receipt = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(receipt["metrics"]["optimized"]["gates"], 2)
            checked = invoke("verify", target)
            self.assertEqual(checked.returncode, 0, checked.stderr)
            self.assertTrue(json.loads(checked.stdout)["verified"])

    def test_compiler_can_print_json_to_stdout(self):
        done = invoke("compile", PROJECT / "examples" / "bell.json")
        self.assertEqual(done.returncode, 0, done.stderr)
        receipt = json.loads(done.stdout)
        self.assertEqual(receipt["metrics"]["optimized"]["gates"], 2)
        self.assertFalse(receipt["scope"]["lean_kernel_verified"])

    def test_demo_displays_exact_amplitudes(self):
        done = invoke("demo", "bell")
        self.assertEqual(done.returncode, 0, done.stderr)
        data = json.loads(done.stdout)
        self.assertEqual(data["basis_amplitudes"]["00"], ["0", "1/2", "0", "0"])
        self.assertEqual(data["basis_amplitudes"]["11"], ["0", "1/2", "0", "0"])
        self.assertEqual(len(data["basis_amplitudes"]), 2)

    def test_bad_input_and_fake_receipt_fail_without_success_json(self):
        with tempfile.TemporaryDirectory() as folder:
            bad = Path(folder) / "bad.json"
            bad.write_text('{"name":"bad","qubits":4,"gates":[{"gate":"CNOT","qubits":[1,1]}]}')
            rejected = invoke("compile", bad)
            self.assertEqual(rejected.returncode, 2)
            self.assertIn("REJECTED", rejected.stderr)
            self.assertEqual(rejected.stdout, "")
            bad.write_text("{invalid json", encoding="utf-8")
            rejected = invoke("compile", bad)
            self.assertEqual(rejected.returncode, 2)
            self.assertIn("REJECTED", rejected.stderr)
            bad.write_text(json.dumps({"verified": True}), encoding="utf-8")
            rejected = invoke("verify", bad)
            self.assertEqual(rejected.returncode, 2)
            self.assertEqual(rejected.stdout, "")

    def test_deeply_nested_json_must_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            bad = Path(folder) / "deep.json"
            bad.write_text("[" * 20000 + "0" + "]" * 20000, encoding="utf-8")
            rejected = invoke("compile", bad)
            self.assertEqual(rejected.returncode, 2, rejected.stderr)
            self.assertIn("REJECTED", rejected.stderr)
            self.assertEqual(rejected.stdout, "")


if __name__ == "__main__":
    unittest.main()
