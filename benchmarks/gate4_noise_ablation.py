"""Gate 4: deterministic noise-mechanism ablations of Gate 3's finding.

POST-HOC, synthetic, historical fake-backend model only.
Uses exact Aer density-matrix probabilities (no Monte Carlo error),
not readout shots. No real-hardware superiority is claimed.

The native logical circuits, physical placement, Qiskit mapping seed and
unitary-equivalence checks are held fixed across noise counterfactuals.
"""
from collections import Counter
from datetime import datetime, timezone
import argparse
import importlib.metadata
import json
import math
from pathlib import Path
import statistics

from benchmarks.gate3_applications import corpus, manifest
from benchmarks.gate3_noisy import sources, tvd
from benchmarks.heldout_compare import prerequisites

CASES = ("phase-cancel-n3", "trotter-ising-n4", "ghz-n3",
         "qaoa-path-n3", "cluster-n3")
SCENARIOS = ("ideal", "readout_only", "calibrated_no_readout",
             "calibrated_with_readout", "calibrated_depolarizing_only",
             "calibrated_relaxation_only", "calibrated_directional_cx_only",
             "direction_swapped_cx_only", "uniform_cx_2percent")
BACKENDS = ("fake_manila", "fake_lagos")
VERSIONS = {"qiskit": "2.6.1", "pyzx": "0.10.8",
            "qiskit-aer": "0.18.4", "qiskit-ibm-runtime": "0.49.0"}
METHODS = ("physqed", "qiskit", "pyzx")
TOL = 2e-7


def version_gate():
    for package, expected in VERSIONS.items():
        got = importlib.metadata.version(package)
        if got != expected:
            raise RuntimeError(f"{package}: expected {expected}, got {got}")


def read_probability_map(value, width):
    """Aer save_probabilities_dict uses hex or binary keys depending on mode."""
    output = {}
    for key, probability in value.items():
        if isinstance(key, str) and key.startswith("0x"):
            numeric = int(key, 16)
        elif isinstance(key, str) and key.startswith("0b"):
            numeric = int(key, 2)
        elif isinstance(key, str) and set(key) <= {"0", "1"}:
            numeric = int(key, 2)
        elif isinstance(key, int):
            numeric = key
        else:
            raise RuntimeError(f"unexpected probability dictionary key: {key!r}")
        if not 0 <= numeric < 1 << width:
            raise RuntimeError("probability key out of measured register range")
        label = format(numeric, f"0{width}b")
        prob = float(probability)
        if not math.isfinite(prob) or prob < -1e-10:
            raise RuntimeError("invalid Aer probability")
        output[label] = output.get(label, 0.) + prob
    if not math.isclose(sum(output.values()), 1., abs_tol=2e-8):
        raise RuntimeError("Aer probabilities fail normalization")
    return output


def unmeasured_native_with_save(native, n):
    """Keep the *mapped* physical qubits for output classical bits 0..n-1."""
    from qiskit_aer.library import save_probabilities_dict

    measures = [instruction for instruction in native.data
                if instruction.operation.name == "measure"]
    if len(measures) != n:
        raise RuntimeError("expect exactly n final native measurements")
    mapping = {}
    for instruction in measures:
        if len(instruction.qubits) != 1 or len(instruction.clbits) != 1:
            raise RuntimeError("malformed mapped measurement")
        logical = native.find_bit(instruction.clbits[0]).index
        physical = native.find_bit(instruction.qubits[0]).index
        if logical in mapping:
            raise RuntimeError("duplicate classical-bit measurement")
        mapping[logical] = physical
    if set(mapping) != set(range(n)) or len(set(mapping.values())) != n:
        raise RuntimeError("missing/duplicate measured bits")
    # Gate 3's circuits have only final measurements, no mid-circuit reset.
    seen_measure = False
    for instruction in native.data:
        if instruction.operation.name == "measure":
            seen_measure = True
        elif seen_measure and instruction.operation.name not in {"barrier"}:
            raise RuntimeError("nonfinal measurement in native candidate")
    qc = native.remove_final_measurements(inplace=False)
    # Qubit sequence 0..n-1 maps to bit positions 0..n-1 in the dictionary.
    qargs = [mapping[c] for c in range(n)]
    save_probabilities_dict(qc, qubits=qargs, label="final_p")
    return qc, qargs


def cx_error_data(backend):
    """Recorded directional CNOT error probabilities on historical target."""
    result = {}
    if "cx" not in backend.target:
        raise RuntimeError("historical backend missing cx gate target")
    for pair, item in backend.target["cx"].items():
        if item is None or item.error is None:
            continue
        p = float(item.error)
        if not 0 <= p < 0.5:
            raise RuntimeError("invalid historical CX error")
        result[tuple(pair)] = p
    if not result:
        raise RuntimeError("no historical CX calibration entries")
    return result


def cx_noise(errors, *, mode, common_p=0.02):
    from qiskit_aer.noise import NoiseModel, depolarizing_error
    nm = NoiseModel()
    mean = statistics.mean(errors.values())
    for edge, calibration in errors.items():
        if mode == "directional":
            p = calibration
        elif mode == "swapped":
            p = errors.get((edge[1], edge[0]), calibration)
        elif mode == "uniform":
            p = common_p
        else:
            raise ValueError("unsupported CX mechanism")
        nm.add_quantum_error(depolarizing_error(p, 2), "cx", list(edge))
    return nm, {"mean_original_cx_error": mean, "uniform_error": common_p,
                "reverse_edge_coverage": sum((j, i) in errors for i, j in errors)}


def backend_readout_matrices(backend):
    """Aer-public readout assignment matrices: rows true, columns recorded."""
    from qiskit_aer.noise.device import basic_device_readout_errors
    result = {}
    for physical_qubits, err in basic_device_readout_errors(target=backend.target):
        if len(physical_qubits) != 1:
            raise RuntimeError("correlated readout not implemented; refuse")
        matrix = [[float(v) for v in row] for row in err.probabilities]
        if len(matrix) != 2 or any(len(row) != 2 for row in matrix):
            raise RuntimeError("only one-qubit 2x2 readout models supported")
        if any(not math.isclose(sum(row), 1., abs_tol=1e-10) for row in matrix):
            raise RuntimeError("bad calibration readout matrix")
        result[physical_qubits[0]] = matrix
    return result


def apply_independent_readout(quantum_p, measured_physical, calibrations):
    """Exact classical assignment-channel push-forward on measured bitstrings.

    At each classical bit c, use the calibration matrix of the physical
    qubit actually measured by that bit, NOT the original logical wire.
    """
    n = len(measured_physical)
    output = {format(i, f"0{n}b"): 0. for i in range(1 << n)}
    eye = ((1., 0.), (0., 1.))
    for true_bits, p in quantum_p.items():
        true = int(true_bits, 2)
        for observed in range(1 << n):
            weight = float(p)
            for c, physical in enumerate(measured_physical):
                matrix = calibrations.get(physical, eye)
                weight *= matrix[(true >> c) & 1][(observed >> c) & 1]
            output[format(observed, f"0{n}b")] += weight
    if not math.isclose(sum(output.values()), sum(quantum_p.values()),
                        abs_tol=2e-8):
        raise RuntimeError("readout assignment channel not stochastic")
    return output


def noise_scenarios(backend):
    from qiskit_aer.noise import NoiseModel
    error_map = cx_error_data(backend)
    directional, props = cx_noise(error_map, mode="directional")
    reverse, _ = cx_noise(error_map, mode="swapped")
    uniform, _ = cx_noise(error_map, mode="uniform")
    return {
        "ideal": None,
        "calibrated_no_readout": NoiseModel.from_backend(
            backend, gate_error=True, readout_error=False,
            thermal_relaxation=True),
        "calibrated_depolarizing_only": NoiseModel.from_backend(
            backend, gate_error=True, readout_error=False,
            thermal_relaxation=False),
        "calibrated_relaxation_only": NoiseModel.from_backend(
            backend, gate_error=False, readout_error=False,
            thermal_relaxation=True),
        "calibrated_directional_cx_only": directional,
        "direction_swapped_cx_only": reverse,
        "uniform_cx_2percent": uniform,
    }, {"historical_cx_errors": {
        f"{i}->{j}": p for (i, j), p in sorted(error_map.items())},
        **props}


def run_density_probabilities(circuit, noise_model, width):
    from qiskit_aer import AerSimulator
    sim = AerSimulator(method="density_matrix", noise_model=noise_model,
                       max_parallel_threads=1)
    result = sim.run(circuit, shots=1).result()
    if not result.success:
        raise RuntimeError("failed deterministic density-matrix evolution")
    return read_probability_map(result.data(0)["final_p"], width)


def gate_ledger(native):
    return [{"name": x.operation.name,
             "physical_qubits": [native.find_bit(q).index for q in x.qubits]}
            for x in native.data]


def audit():
    version_gate()
    QuantumCircuit, transpile, qasm2, Operator, pyzx = prerequisites()
    from qiskit.quantum_info import Statevector
    from qiskit_ibm_runtime.fake_provider import FakeManilaV2, FakeLagosV2

    cases = {r["name"]: r for r in corpus()}
    if set(CASES) - set(cases):
        raise RuntimeError("missing Gate 3 application fixture")
    models = (FakeManilaV2(), FakeLagosV2())
    report = {
        "schema": "physqed-q-gate4-deterministic-noise-causal-ablation-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "app_manifest": manifest(),
        "predeclared_case_names": list(CASES),
        "predeclared_scenarios": list(SCENARIOS),
        "posthoc_study": True,
        "live_hardware": False,
        "sampled_shots": False,
        "no_sampling_error_intervals": True,
        "no_calibration_uncertainty_bounds": True,
        "interpretation": (
            "Model-based counterfactual mechanisms only; ablations need not "
            "decompose effects additively. No real physical causal inference."
        ),
        "backends": [],
    }
    for backend in models:
        if backend.name not in BACKENDS:
            raise RuntimeError("unexpected historical backend")
        noise_models, calibration = noise_scenarios(backend)
        assignment_matrices = backend_readout_matrices(backend)
        props = backend.properties()
        section = {
            "name": backend.name, "num_physical_qubits": backend.num_qubits,
            "historical_calibration_time": str(props.last_update_date),
            "cx_calibration": calibration,
            "readout_calibration_by_physical_qubit": assignment_matrices,
            "cases": [],
        }
        for name in CASES:
            raw = cases[name]["circuit"]
            n = raw["qubits"]
            original, outputs, receipt, zx_t = sources(
                raw, QuantumCircuit, transpile, qasm2, Operator, pyzx)
            v = Statevector.from_instruction(original).probabilities()
            target = {format(i, f"0{n}b"): float(p) for i, p in enumerate(v)}
            row = {
                "name": name, "qubits": n,
                "ideal_target_probabilities": target,
                "full_operator_equivalence": True,
                "physqed_exact_receipt_hash": receipt["receipt_sha256"],
                "methods": {}, "contrasts": {},
            }
            for method in METHODS:
                measured = outputs[method].copy()
                measured.measure_all()
                mapped = transpile(
                    measured, backend=backend, optimization_level=3,
                    seed_transpiler=2026, initial_layout=list(range(n)))
                circuit, measured_physical = unmeasured_native_with_save(mapped, n)
                route = gate_ledger(mapped)
                info = {
                    "native_operations": route,
                    "measurement_physical_qubits_for_classical_bits": measured_physical,
                    "native_cx_sequence": [x["physical_qubits"] for x in route
                                          if x["name"] == "cx"],
                    "cx_count": sum(x["name"] == "cx" for x in route),
                    "scenario_tvd": {}, "scenario_probabilities": {},
                }
                for scenario in SCENARIOS:
                    if scenario == "readout_only":
                        probabilities = apply_independent_readout(
                            info["scenario_probabilities"]["ideal"],
                            measured_physical, assignment_matrices)
                    elif scenario == "calibrated_with_readout":
                        probabilities = apply_independent_readout(
                            info["scenario_probabilities"]["calibrated_no_readout"],
                            measured_physical, assignment_matrices)
                    else:
                        probabilities = run_density_probabilities(
                            circuit, noise_models[scenario], n)
                    d = tvd(probabilities, target)
                    if scenario == "ideal" and d > TOL:
                        raise RuntimeError("exact noiseless routing control failed")
                    info["scenario_tvd"][scenario] = d
                    info["scenario_probabilities"][scenario] = probabilities
                row["methods"][method] = info
            for comparator in ("qiskit", "pyzx"):
                row["contrasts"][comparator] = {}
                for scenario in SCENARIOS:
                    a = row["methods"]["physqed"]["scenario_tvd"][scenario]
                    b = row["methods"][comparator]["scenario_tvd"][scenario]
                    row["contrasts"][comparator][scenario] = {
                        "phys_minus_baseline_tvd": a-b,
                        "phys_better_within_fixed_model": a + TOL < b,
                        "phys_worse_within_fixed_model": b + TOL < a,
                    }
            section["cases"].append(row)
        report["backends"].append(section)
    report["summary"] = {
        backend["name"]: {
            scenario: {
                comparison: {
                    "phys_better": sum(
                        c["contrasts"][comparison][scenario][
                            "phys_better_within_fixed_model"]
                        for c in backend["cases"]),
                    "phys_worse": sum(
                        c["contrasts"][comparison][scenario][
                            "phys_worse_within_fixed_model"]
                        for c in backend["cases"]),
                    "approximately_equal": sum(
                        not (c["contrasts"][comparison][scenario][
                             "phys_better_within_fixed_model"] or
                             c["contrasts"][comparison][scenario][
                             "phys_worse_within_fixed_model"])
                        for c in backend["cases"]),
                } for comparison in ("qiskit", "pyzx")
            } for scenario in SCENARIOS
        } for backend in report["backends"]
    }
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    report = audit()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, sort_keys=True, indent=2)+"\n")
    compact = {}
    for backend in report["backends"]:
        phase = next(row for row in backend["cases"] if row["name"]=="phase-cancel-n3")
        compact[backend["name"]] = {
            "phase_cancel_n3": {
                scenario: {
                    "phys_minus_pyzx": phase["contrasts"]["pyzx"][scenario][
                        "phys_minus_baseline_tvd"],
                    "phys_minus_qiskit": phase["contrasts"]["qiskit"][scenario][
                        "phys_minus_baseline_tvd"],
                } for scenario in SCENARIOS
            },
            "cases": len(backend["cases"]),
            "historical_calibration": backend["historical_calibration_time"],
        }
    print(json.dumps({"source_manifest":report["app_manifest"]["sha256"],
                      "no_hardware_claim":True, "shotless":True,
                      "study":compact}, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
