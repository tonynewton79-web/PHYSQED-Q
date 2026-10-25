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
    def test_cli_optimality_round_trip(self):
        circuit = {"name": "H-X-H witness", "qubits": 1, "gates": [
            {"gate": "H", "qubits": [0]}, {"gate": "X", "qubits": [0]},
            {"gate": "H", "qubits": [0]},
        ]}
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "circuit.json"
            target = Path(folder) / "optimality.json"
            source.write_text(json.dumps(circuit), encoding="utf-8")
            made = invoke("synthesize", source, "--horizon", "5", "--output", target)
            self.assertEqual(made.returncode, 0, made.stderr)
            receipt = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(receipt["schema"], "physqed-q-bounded-optimality-v1")
            self.assertEqual(receipt["optimized"], {"name": circuit["name"], "qubits": 1,
                             "gates": [{"gate": "Z", "qubits": [0]}]})
            self.assertEqual(receipt["search"]["words_examined"], 19608)
            self.assertEqual(json.loads(made.stdout), {
                "written": str(target), "receipt_sha256": receipt["receipt_sha256"],
                "equivalence_verified": True})
            checked = invoke("verify-optimality", target)
            self.assertEqual(checked.returncode, 0, checked.stderr)
            result = json.loads(checked.stdout)
            self.assertTrue(result["verified"])
            self.assertEqual(result["minimum_gates"], 1)
            self.assertEqual(result["words_examined"], 19608)
            self.assertFalse(result["lean_kernel_verified"])
            self.assertFalse(result["hardware_verified"])
            printed = invoke("synthesize", source, "--horizon", "1")
            self.assertEqual(printed.returncode, 0, printed.stderr)
            self.assertEqual(json.loads(printed.stdout)["optimized"], receipt["optimized"])
            # Bounded synthesis is separate: the default rewrite compiler stays v1.
            legacy = invoke("compile", source, "--output", target)
            self.assertEqual(legacy.returncode, 0, legacy.stderr)
            old_receipt = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(old_receipt["schema"], "physqed-q-exact-receipt-v1")
            self.assertEqual(old_receipt["optimized"], receipt["optimized"])
            self.assertEqual([step["rule"] for step in old_receipt["steps"]], ["HXH_to_Z"])
            replayed = invoke("verify", target)
            self.assertEqual(replayed.returncode, 0, replayed.stderr)
            self.assertTrue(json.loads(replayed.stdout)["verified"])

    def test_cli_optimality_rejects_out_of_scope(self):
        circuit = {"name": "No one-gate representative", "qubits": 1, "gates": [
            {"gate": "H", "qubits": [0]}, {"gate": "T", "qubits": [0]},
        ]}
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "circuit.json"
            target = Path(folder) / "receipt.json"
            source.write_text(json.dumps(circuit), encoding="utf-8")
            for horizon in ["-1", "6", "1.0", "true", "1"]:
                with self.subTest(horizon=horizon):
                    rejected = invoke("synthesize", source, "--horizon", horizon,
                                      "--output", target)
                    self.assertEqual(rejected.returncode, 2, rejected.stderr)
                    self.assertEqual(rejected.stdout, "")
                    self.assertFalse(target.exists())
                    self.assertIn("horizon" if horizon != "1" else "no exact representative",
                                  rejected.stderr)
            for payload in ['{"name":"a","name":"b","qubits":1,"gates":[]}',
                            " " * 262145, '{"verified":true}', "{invalid json"]:
                source.write_text(payload, encoding="utf-8")
                for command in ["synthesize", "verify-optimality"]:
                    with self.subTest(command=command, payload_size=len(payload)):
                        rejected = invoke(command, source)
                        self.assertEqual(rejected.returncode, 2, rejected.stderr)
                        self.assertEqual(rejected.stdout, "")
                        self.assertIn("REJECTED", rejected.stderr)

    def test_optimizer_is_opt_in_and_commuting_receipt_replays(self):
        circuit = {"name": "Interleaved", "qubits": 2, "gates": [
            {"gate": "H", "qubits": [0]}, {"gate": "X", "qubits": [1]},
            {"gate": "H", "qubits": [0]},
        ]}
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "circuit.json"
            target = Path(folder) / "receipt.json"
            source.write_text(json.dumps(circuit), encoding="utf-8")
            default = invoke("compile", source)
            self.assertEqual(default.returncode, 0, default.stderr)
            legacy = json.loads(default.stdout)
            self.assertEqual(legacy["schema"], "physqed-q-exact-receipt-v1")
            self.assertEqual(len(legacy["optimized"]["gates"]), 3)
            made = invoke("compile", source, "--optimizer", "commuting", "--output", target)
            self.assertEqual(made.returncode, 0, made.stderr)
            receipt = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(receipt["schema"], "physqed-q-exact-receipt-v2")
            self.assertEqual(receipt["optimized"]["gates"], [{"gate": "X", "qubits": [1]}])
            self.assertFalse(receipt["scope"]["lean_kernel_verified"])
            checked = invoke("verify", target)
            self.assertEqual(checked.returncode, 0, checked.stderr)
            self.assertTrue(json.loads(checked.stdout)["verified"])
            explicit = invoke("compile", source, "--optimizer", "adjacent")
            self.assertEqual(explicit.returncode, 0, explicit.stderr)
            self.assertEqual(json.loads(explicit.stdout), legacy)
            rejected = invoke("compile", source, "--optimizer", "unknown")
            self.assertEqual(rejected.returncode, 2)
            self.assertEqual(rejected.stdout, "")

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
