"""Matched-workload external compiler and historical calibration-snapshot audit.

Pinned Qiskit/PyZX/IBM-runtime dependencies are required; no silent fallback.
All logical candidates undergo independent matrix comparison up to global
phase; PHYSQED receipts additionally receive exact Q(sqrt(2),i) replay.
The FakeManilaV2 backend is a *historical* calibration snapshot, NOT a live
device. Gate-error product and ASAP times are simple cost proxies, NOT
measured fidelity. A non-equivalent external output is recorded, not ranked.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import time

from benchmarks.heldout_suite import generate, manifest
from physqed_q.compiler import compile_circuit, verify_receipt

FIXED_SEED = 2026
NATIVE_CASES_PER_FAMILY = 5
BASIS = ["h", "x", "z", "s", "sdg", "t", "tdg", "cx", "cz", "swap"]
EXPECTED_QISKIT = "2.6.1"
EXPECTED_PYZX = "0.10.8"


def prerequisites():
    from qiskit import QuantumCircuit, transpile, qasm2
    from qiskit.quantum_info import Operator
    import pyzx
    if importlib.metadata.version("qiskit") != EXPECTED_QISKIT:
        raise RuntimeError("Qiskit version mismatch (requires 2.6.1)")
    if importlib.metadata.version("pyzx") != EXPECTED_PYZX:
        raise RuntimeError("PyZX version mismatch (requires 0.10.8)")
    return QuantumCircuit, transpile, qasm2, Operator, pyzx


def qiskit_input(raw, QuantumCircuit):
    result = QuantumCircuit(raw["qubits"])
    for op in raw["gates"]:
        name = {"CNOT": "cx"}.get(op["gate"], op["gate"].lower())
        getattr(result, name)(*op["qubits"])
    return result


def logical_stats(circuit, *, t_override=None):
    counts = Counter(item.operation.name for item in circuit.data)
    allowed = set(BASIS)
    return {
        "gates": circuit.size(),
        "depth": circuit.depth() or 0,
        "two_qubit": sum(len(item.qubits) == 2 for item in circuit.data),
        "t_count": (
            int(t_override) if t_override is not None else
            int(counts["t"] + counts["tdg"]) if set(counts).issubset(allowed)
            else None
        ),
        "gate_names": dict(sorted(counts.items())),
        "non_clifford_resource_evaluable": t_override is not None
        or set(counts).issubset(allowed),
    }


def same_operator(a, b, Operator):
    # Global-phase insensitive equivalence is the physically meaningful
    # common baseline. This numerical check is NOT the exact Python replay.
    import numpy as np
    if a.num_qubits != b.num_qubits:
        return False
    U = Operator(a).data
    V = Operator(b).data
    z = np.vdot(U.ravel(), V.ravel())
    if abs(z) < 1.e-12:
        return False
    phase = z / abs(z)
    return bool(np.allclose(V, phase * U, rtol=0, atol=1.e-9))


def native_snapshot():
    from qiskit_ibm_runtime.fake_provider import FakeManilaV2
    backend = FakeManilaV2()
    if backend.num_qubits < 4:
        raise RuntimeError("snapshot backend has fewer than four qubits")
    try:
        props = backend.properties()
        last_cal = str(props.last_update_date)
    except (AttributeError, ValueError):
        last_cal = None
    return backend, {
        "backend": backend.name,
        "historical_fake_backend": True,
        "physical_experiment": False,
        "snapshot_calibration_date": last_cal,
        "runtime_version": importlib.metadata.version("qiskit-ibm-runtime"),
        "n_physical_qubits": backend.num_qubits,
    }


def native_cost(circuit, backend, transpile):
    # All logical frontends are routed against *the same physical wire
    # allocation*, preset level, backend target and seed.
    mapped = transpile(circuit, backend=backend, optimization_level=3,
                       initial_layout=list(range(circuit.num_qubits)),
                       seed_transpiler=FIXED_SEED)
    clock = [0.] * mapped.num_qubits
    survival = 1.
    missing = []
    gate_counts = Counter()
    for entry in mapped.data:
        name = entry.operation.name
        if name == "barrier":
            continue
        qargs = tuple(mapped.find_bit(q).index for q in entry.qubits)
        props = backend.target.get(name, {}).get(qargs)
        if props is None or props.duration is None or props.error is None:
            missing.append({"gate": name, "qubits": list(qargs)})
            continue
        duration, error = props.duration, props.error
        if not (0 <= duration < float("inf") and 0 <= error < 1):
            raise RuntimeError(f"invalid historical calibration: {name}, {qargs}")
        start = max((clock[q] for q in qargs), default=0.)
        for q in qargs:
            clock[q] = start + duration
        survival *= 1 - error
        gate_counts[name] += 1
    return {
        "native_gate_counts": dict(sorted(gate_counts.items())),
        "native_two_qubit": sum(len(entry.qubits) == 2 for entry in mapped.data),
        "duration_seconds_proxy": max(clock, default=0.) if not missing else None,
        "independent_gate_survival_proxy": survival if not missing else None,
        "complete_calibration": not missing,
        "missing_instruction_properties": missing,
        "calibration_model": "ASAP durations; independent gate error product; no readout, idle decoherence or crosstalk",
    }


def evaluate(split="heldout", *, native=True):
    QuantumCircuit, transpile, qasm2, Operator, pyzx = prerequisites()
    backend, snapshot = native_snapshot() if native else (None, None)
    cases = generate(split)
    report = {
        "schema": "physqed-q-matched-external-historical-snapshot-v1",
        "methodology": "precommitted synthetic fixed-seed split, no tuning on heldout output",
        "disclaimer": "No general T-count superiority, current calibration, real QPU or fidelity improvement established",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "manifest": manifest(split),
        "software": {"qiskit": EXPECTED_QISKIT, "pyzx": EXPECTED_PYZX,
                     "physqed_optimizer": "phase"},
        "settings": {"seed_transpiler": FIXED_SEED, "optimization_level": 3,
                     "logical_basis": BASIS, "native_case_count_per_family":
                     NATIVE_CASES_PER_FAMILY, "snapshot": snapshot},
        "cases": [],
    }
    summary = Counter()
    for case in cases:
        raw = case["circuit"]
        original = qiskit_input(raw, QuantumCircuit)
        row = {"name": case["name"], "family": case["family"],
               "width": raw["qubits"], "original": logical_stats(original),
               "logical": {}, "native": {}, "errors": {}}
        compilers = {}
        # Exact PHYSQED-Q gate-by-gate checked receipt.
        t0 = time.monotonic()
        receipt = compile_circuit(raw, optimizer="phase")
        check = verify_receipt(receipt)
        if not check["verified"]:
            raise RuntimeError("PHYSQED exact replay failed")
        out = qiskit_input(receipt["optimized"], QuantumCircuit)
        if not same_operator(original, out, Operator):
            raise RuntimeError("PHYSQED/Qiskit independent operator mismatch")
        row["logical"]["physqed"] = logical_stats(out)
        row["logical"]["physqed"]["exact_replay"] = True
        row["logical"]["physqed"]["seconds"] = time.monotonic()-t0
        compilers["physqed"] = out
        # Qiskit native gate-alphabet, no hardware topology at logical stage.
        t0 = time.monotonic()
        try:
            qout = transpile(original, basis_gates=BASIS, optimization_level=3,
                             seed_transpiler=FIXED_SEED)
            valid = same_operator(original, qout, Operator)
            row["logical"]["qiskit"] = logical_stats(qout)
            row["logical"]["qiskit"]["equivalent_up_to_global_phase"] = valid
            row["logical"]["qiskit"]["seconds"] = time.monotonic()-t0
            if valid:
                compilers["qiskit"] = qout
            else:
                summary["qiskit_non_equivalent"] += 1
        except Exception as exc:
            row["errors"]["qiskit"] = f"{type(exc).__name__}: {exc}"
            summary["qiskit_exception"] += 1
        # Actual PyZX phase-polynomial / TODD-based full optimization.
        t0 = time.monotonic()
        try:
            source = pyzx.Circuit.from_qasm(qasm2.dumps(original))
            pout = pyzx.optimize.full_optimize(source.to_basic_gates())
            parsed = QuantumCircuit.from_qasm_str(pout.to_qasm())
            valid = same_operator(original, parsed, Operator)
            row["logical"]["pyzx"] = logical_stats(parsed,
                                                   t_override=pout.tcount())
            row["logical"]["pyzx"]["equivalent_up_to_global_phase"] = valid
            row["logical"]["pyzx"]["seconds"] = time.monotonic()-t0
            if valid:
                compilers["pyzx"] = parsed
            else:
                summary["pyzx_non_equivalent"] += 1
        except Exception as exc:
            row["errors"]["pyzx"] = f"{type(exc).__name__}: {exc}"
            summary["pyzx_exception"] += 1
        # Count strictly paired valid logical candidates only.
        for baseline in ("qiskit", "pyzx"):
            info = row["logical"].get(baseline, {})
            a, b = row["logical"]["physqed"]["t_count"], info.get("t_count")
            if baseline in compilers and b is not None:
                summary[f"{baseline}_paired"] += 1
                summary[f"physqed_lt_{baseline}"] += a < b
                summary[f"physqed_eq_{baseline}"] += a == b
                summary[f"physqed_gt_{baseline}"] += a > b
        if native and int(case["name"].rsplit("-", 1)[1]) < NATIVE_CASES_PER_FAMILY:
            for label, candidate in compilers.items():
                try:
                    row["native"][label] = native_cost(candidate, backend, transpile)
                    if row["native"][label]["complete_calibration"]:
                        summary[f"{label}_native_complete"] += 1
                    else:
                        summary[f"{label}_native_incomplete"] += 1
                except Exception as exc:
                    row["errors"][f"native_{label}"] = f"{type(exc).__name__}: {exc}"
                    summary[f"{label}_native_exception"] += 1
            # Only complete, matched baseline pairs enter proxy comparisons.
            for baseline in ("qiskit", "pyzx"):
                a, b = row["native"].get("physqed", {}), row["native"].get(baseline, {})
                if a.get("complete_calibration") and b.get("complete_calibration"):
                    summary[f"{baseline}_native_paired"] += 1
                    for metric in ("native_two_qubit", "duration_seconds_proxy"):
                        if a[metric] < b[metric] - 1.e-15:
                            summary[f"physqed_native_lt_{baseline}_{metric}"] += 1
                        elif a[metric] > b[metric] + 1.e-15:
                            summary[f"physqed_native_gt_{baseline}_{metric}"] += 1
                        else:
                            summary[f"physqed_native_eq_{baseline}_{metric}"] += 1
        summary["total_cases"] += 1
        report["cases"].append(row)
    report["summary"] = dict(sorted(summary.items()))
    return report


def short_summary(report):
    s = report["summary"]
    return ("N={total_cases};Q={qiskit_paired};Z={pyzx_paired};"
            "P<Q={physqed_lt_qiskit};P=Q={physqed_eq_qiskit};"
            "P>Q={physqed_gt_qiskit};P<Z={physqed_lt_pyzx};"
            "P=Z={physqed_eq_pyzx};P>Z={physqed_gt_pyzx};"
            "fake={physqed_native_complete}").format_map(
                {k: s.get(k, 0) for k in (
                    "total_cases", "qiskit_paired", "pyzx_paired",
                    "physqed_lt_qiskit", "physqed_eq_qiskit",
                    "physqed_gt_qiskit", "physqed_lt_pyzx",
                    "physqed_eq_pyzx", "physqed_gt_pyzx",
                    "physqed_native_complete")})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=("dev", "heldout"), default="heldout")
    parser.add_argument("--no-native", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()
    result = evaluate(args.split, native=not args.no_native)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    label = short_summary(result)
    print(label)
    print("manifest: " + result["manifest"]["sha256"])
    print("status details in " + str(args.output))
    if args.github_output:
        with args.github_output.open("a", encoding="utf8") as stream:
            stream.write("short_summary=" + label + "\n")
    # Fail closed if any baseline failed: do not silently select only
    # successful external outputs and call that a fair benchmark.
    s = result["summary"]
    if s.get("qiskit_paired", 0) != len(result["cases"]) or s.get(
            "pyzx_paired", 0) != len(result["cases"]):
        raise SystemExit("Incomplete paired comparison: inspect failure report")
    if not args.no_native:
        expected = 4 * NATIVE_CASES_PER_FAMILY
        if any(s.get(f"{name}_native_complete", 0) != expected
               for name in ("physqed", "qiskit", "pyzx")):
            raise SystemExit("Incomplete historical snapshot comparison")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
