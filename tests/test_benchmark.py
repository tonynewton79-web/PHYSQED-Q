"""Public-data benchmark contract; no comparison implies quantum advantage."""

import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

from benchmarks.qiskit_compare import BenchmarkError, compare, from_qiskit


EXAMPLE = {
    "name": "trial",
    "qubits": 2,
    "gates": [
        {"gate": "H", "qubits": [0]},
        {"gate": "Z", "qubits": [0]},
        {"gate": "H", "qubits": [0]},
        {"gate": "CNOT", "qubits": [0, 1]},
        {"gate": "CNOT", "qubits": [0, 1]},
    ],
}


class BenchmarkValidationTests(unittest.TestCase):
    def test_reject_invalid_level_and_seed_before_optional_import(self):
        for level in (-1, 4, True, "1"):
            with self.subTest(level=level), self.assertRaises(BenchmarkError):
                compare(EXAMPLE, level=level)
        for seed in (-1, True, 2**32, "2026"):
            with self.subTest(seed=seed), self.assertRaises(BenchmarkError):
                compare(EXAMPLE, seed=seed)

    def test_invalid_circuit_never_runs_external_compiler(self):
        bad = {**EXAMPLE, "qubits": 5}
        with self.assertRaises(BenchmarkError):
            compare(bad)

    def test_benchmark_cli_rejects_ambiguous_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ambiguous.json"
            path.write_text('{"name":"x","qubits":1,"qubits":2,"gates":[]}')
            proc = subprocess.run(
                [sys.executable, "-m", "benchmarks.qiskit_compare", str(path)],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(proc.returncode, 2)
            self.assertIn("duplicate", proc.stderr.lower())


@unittest.skipUnless(importlib.util.find_spec("qiskit"), "optional Qiskit not installed")
class LiveQiskitTests(unittest.TestCase):
    def test_real_qiskit_comparison_reports_version_settings_and_metrics(self):
        result = compare(EXAMPLE, level=1, seed=2026)
        self.assertEqual(result["schema"], "physqed-q-qiskit-comparison-v1")
        self.assertEqual(result["settings"]["seed_transpiler"], 2026)
        self.assertEqual(result["settings"]["optimization_level"], 1)
        self.assertTrue(result["qiskit"]["version"])
        self.assertEqual(result["physqed_q"]["input_metrics"]["gates"], 5)
        self.assertEqual(result["physqed_q"]["optimized_metrics"]["gates"], 1)
        self.assertIsInstance(result["qiskit"]["output_metrics"]["gates"], int)
        self.assertIn(result["qiskit"]["exact_operator_equivalent"], (True, False, None))

    def test_reject_unsupported_parameter_gate(self):
        from qiskit import QuantumCircuit
        output = QuantumCircuit(1)
        output.rx(0.5, 0)
        with self.assertRaisesRegex(BenchmarkError, "unsupported"):
            from_qiskit(output, "rx")

    def test_reject_nonzero_global_phase_for_strict_equality(self):
        from qiskit import QuantumCircuit
        output = QuantumCircuit(1, global_phase=0.5)
        output.x(0)
        with self.assertRaisesRegex(BenchmarkError, "global phase"):
            from_qiskit(output, "phase")

    def test_flags_different_operators_without_claiming_compiler_error(self):
        from qiskit import QuantumCircuit
        from physqed_q.kernel import unitary
        output = QuantumCircuit(1)
        output.z(0)
        parsed = from_qiskit(output, "trial")
        source = {"name": "trial", "qubits": 1,
                  "gates": [{"gate": "X", "qubits": [0]}]}
        self.assertNotEqual(unitary(parsed), unitary(source))


if __name__ == "__main__":
    unittest.main()
