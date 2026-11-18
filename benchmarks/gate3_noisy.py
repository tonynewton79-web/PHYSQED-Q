"""Gate 3: noisy, historical-calibration application-circuit comparison.

A simulator study only. This module never claims live superconducting
measurements or present-day calibrations. Every candidate must be logically
equivalent to the SAME target before entering a noise-model comparison.
Uses Qiskit 2.6.1, PyZX 0.10.8, Aer 0.18.4 and the historical
IBM FakeManilaV2 backend from IBM Runtime 0.49.0.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import importlib.metadata
import json
import math
from pathlib import Path

from benchmarks.gate3_applications import corpus, manifest
from benchmarks.heldout_compare import (
    prerequisites, qiskit_input, logical_stats, same_operator,
)
from physqed_q.compiler import compile_circuit, verify_receipt

AER_VERSION = "0.18.4"
SHOTS = 4096
SEEDS = (20261118, 20261119)
TRANSPILER_SEED = 2026
ALPHA = 0.05
EXPECTED_CASES = 15
N_COMPILERS = 3
MAX_OUTCOMES = 16


def tvd(p, q):
    """Total variation distance between normalized finite distributions."""
    keys = set(p) | set(q)
    return .5 * sum(abs(p.get(k, 0.) - q.get(k, 0.)) for k in keys)


def radius_bhc(outcomes, shots, tests, alpha=ALPHA):
    """Union-BHC total-variation error bound at familywise level alpha.

    For m outcomes and independent draws, P(TV(phat,p)>e)
    <= 2^m exp(-2*N*e^2).
    A union over 'tests' distributions makes the radius simultaneous.
    This is a *Monte Carlo sampling* bound, not a calibration uncertainty
    interval or a statement about real-device experimental errors.
    """
    if not (type(outcomes) is int and 1 <= outcomes <= 16 and
            type(shots) is int and shots >= 1 and
            type(tests) is int and tests >= 1 and
            0 < alpha < 1):
        raise ValueError("invalid concentration-bound parameters")
    return min(1., math.sqrt(
        (outcomes * math.log(2) + math.log(tests / alpha)) / (2 * shots)
    ))


def paired_status(a, b, ra, rb):
    """A is better/worse only if simultaneous TV uncertainty is separated."""
    margin = ra + rb
    if a + margin < b:
        return "certified_better_under_fixed_noise_model"
    if b + margin < a:
        return "certified_worse_under_fixed_noise_model"
    return "inconclusive_sampling_bound"


def sources(raw, QuantumCircuit, transpile, qasm2, Operator, pyzx):
    original = qiskit_input(raw, QuantumCircuit)
    outputs = {}
    receipt = compile_circuit(raw, optimizer="phase")
    if not verify_receipt(receipt)["verified"]:
        raise RuntimeError("PHYSQED exact replay failed")
    outputs["physqed"] = qiskit_input(receipt["optimized"], QuantumCircuit)
    outputs["qiskit"] = transpile(
        original,
        basis_gates=["h", "x", "z", "s", "sdg", "t", "tdg",
                     "cx", "cz", "swap"],
        optimization_level=3, seed_transpiler=TRANSPILER_SEED
    )
    source_zx = pyzx.Circuit.from_qasm(qasm2.dumps(original))
    zx = pyzx.optimize.full_optimize(source_zx.to_basic_gates())
    outputs["pyzx"] = QuantumCircuit.from_qasm_str(zx.to_qasm())
    for name, output in outputs.items():
        if output.num_qubits != original.num_qubits:
            raise RuntimeError(name + " altered logical register size")
        if not same_operator(original, output, Operator):
            raise RuntimeError(name + " output not unitary-equivalent")
    return original, outputs, receipt, zx.tcount()


def prob_from_counts(counts, width):
    n = sum(counts.values())
    if n <= 0:
        raise RuntimeError("empty measurement counts")
    p = {}
    for key, val in counts.items():
        bits = key.replace(" ", "")
        if len(bits) != width or any(ch not in "01" for ch in bits):
            raise RuntimeError("unexpected classical measurement register")
        p[bits] = p.get(bits, 0.) + val / n
    return p


def noisy_counts(simulator, physical, shots, seeds):
    all_counts = Counter()
    for seed in seeds:
        result = simulator.run(physical, shots=shots, seed_simulator=seed).result()
        if not result.success:
            raise RuntimeError("Aer noisy simulation failed")
        all_counts.update(result.get_counts(0))
    return all_counts


def study(*, limit=None):
    QuantumCircuit, transpile, qasm2, Operator, pyzx = prerequisites()
    import qiskit_aer
    from qiskit_aer import AerSimulator
    from qiskit_ibm_runtime.fake_provider import FakeManilaV2
    from qiskit.quantum_info import Statevector

    if qiskit_aer.__version__ != AER_VERSION:
        raise RuntimeError("Qiskit Aer version mismatch")
    backend = FakeManilaV2()
    props = backend.properties()
    original_cases = corpus()
    if len(original_cases) != EXPECTED_CASES:
        raise RuntimeError("application corpus cardinality changed")
    cases = original_cases if limit is None else original_cases[:limit]
    noise_sim = AerSimulator.from_backend(backend, method="density_matrix")
    noise_sim.set_options(max_parallel_threads=1)
    ideal_sim = AerSimulator(method="statevector", max_parallel_threads=1)
    total_shots = SHOTS * len(SEEDS)
    # Familywise 95% bound over all 15*3 noisy distributions and 15*3
    # noiseless routing-control distributions; no selective CI inference.
    n_distributions = EXPECTED_CASES * N_COMPILERS * 2
    rows = []
    summary = Counter()
    for case in cases:
        raw = case["circuit"]
        width = raw["qubits"]
        original, candidates, receipt, zx_tcount = sources(
            raw, QuantumCircuit, transpile, qasm2, Operator, pyzx)
        target_probs_arr = Statevector.from_instruction(original).probabilities()
        target = {format(i, f"0{width}b"): float(value)
                  for i, value in enumerate(target_probs_arr)}
        row = {"name": case["name"], "family": case["family"],
               "qubits": width, "ideal_distribution": target, "compilers": {},
               "comparisons": {}}
        r = radius_bhc(2 ** width, total_shots, n_distributions)
        for name in ("physqed", "qiskit", "pyzx"):
            logical = candidates[name]
            if not same_operator(original, logical, Operator):
                raise RuntimeError("repeated logical equivalence check failed")
            measured = logical.copy()
            measured.measure_all()
            mapped = transpile(
                measured, backend=backend, optimization_level=3,
                initial_layout=list(range(width)),
                seed_transpiler=TRANSPILER_SEED)
            ideal_counts = noisy_counts(ideal_sim, mapped, SHOTS, SEEDS)
            ideal_measured = prob_from_counts(ideal_counts, width)
            ideal_routing_tvd = tvd(ideal_measured, target)
            if ideal_routing_tvd > 0.10:
                raise RuntimeError(
                    "ideal mapped output differs from intended logical distribution")
            actual_counts = noisy_counts(noise_sim, mapped, SHOTS, SEEDS)
            observed = prob_from_counts(actual_counts, width)
            d = tvd(observed, target)
            gate_counts = Counter(g.operation.name for g in mapped.data)
            info = {
                "logical": logical_stats(logical),
                "native_gate_counts": dict(sorted(gate_counts.items())),
                "native_two_qubit": sum(
                    len(g.qubits) == 2 for g in mapped.data),
                "tvd_noiseless_routing_control": ideal_routing_tvd,
                "tvd_noisy_vs_ideal": d,
                "tvd_noise_model_confidence_radius": r,
                "counts": dict(sorted(actual_counts.items())),
                "ideal_counts": dict(sorted(ideal_counts.items())),
                "logical_equivalence_checked": True,
                "physqed_exact_receipt_replayed": name == "physqed",
            }
            if name == "pyzx":
                info["logical"]["t_count"] = zx_tcount
            if name == "physqed":
                info["exact_receipt_sha256"] = receipt["receipt_sha256"]
            row["compilers"][name] = info
            summary[f"{name}_cases"] += 1
        for base in ("qiskit", "pyzx"):
            a, b = row["compilers"]["physqed"], row["compilers"][base]
            decision = paired_status(a["tvd_noisy_vs_ideal"],
                                     b["tvd_noisy_vs_ideal"], r, r)
            row["comparisons"][base] = {
                "delta_tvd_phys_minus_baseline":
                    a["tvd_noisy_vs_ideal"]-b["tvd_noisy_vs_ideal"],
                "simultaneous_sampling_bound_decision": decision,
                "threshold_tvd_difference": 2*r,
            }
            summary[f"{base}_{decision}"] += 1
            summary[f"{base}_phys_lower_native_two_qubit"] += (
                a["native_two_qubit"] < b["native_two_qubit"])
            summary[f"{base}_phys_higher_native_two_qubit"] += (
                a["native_two_qubit"] > b["native_two_qubit"])
            summary[f"{base}_phys_equal_native_two_qubit"] += (
                a["native_two_qubit"] == b["native_two_qubit"])
        rows.append(row)
    result = {
        "schema": "physqed-q-gate3-noisy-applications-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "application_manifest": manifest(),
        "tested_cases": len(cases),
        "gate3_full_application_count": EXPECTED_CASES,
        "study_type": "historical_backend_noisy_simulation",
        "not_real_hardware": True,
        "not_live_calibration": True,
        "no_general_superiority_claim": True,
        "snapshot": {
            "backend": backend.name, "qubits": backend.num_qubits,
            "last_calibrated": str(props.last_update_date),
            "runtime": importlib.metadata.version("qiskit-ibm-runtime"),
        },
        "versions": {
            "qiskit": importlib.metadata.version("qiskit"),
            "pyzx": importlib.metadata.version("pyzx"),
            "aer": AER_VERSION,
        },
        "simulation": {
            "shots_per_seed": SHOTS, "seeds": list(SEEDS),
            "shots_per_candidate": total_shots,
            "seed_transpiler": TRANSPILER_SEED,
            "logical_check": "full operator up to global phase, tolerance 1e-9",
            "physqed_additional_check": "exact full-operator receipt replay",
            "noise_source": "AerSimulator.from_backend(FakeManilaV2)",
            "noiseless_mapping_control": "no-noise Aer sampling on same native circuit",
            "readout_noise_included": True,
            "tvd_sampling_bound": "simultaneous BHC/union-bound for all 90 distribution estimates; no calibration uncertainty",
            "familywise_alpha": ALPHA,
            "bound_audit_distributions": n_distributions,
        },
        "summary": dict(sorted(summary.items())),
        "cases": rows,
    }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    if args.limit is not None and not 1 <= args.limit <= EXPECTED_CASES:
        raise SystemExit("limit must be 1..15")
    result = study(limit=args.limit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                           encoding="utf8")
    print(json.dumps({"manifest": result["application_manifest"]["sha256"],
                      "summary": result["summary"], "cases": result["tested_cases"],
                      "backend": result["snapshot"], "path": str(args.output)},
                     indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
