"""Post-hoc cross-backend, independent-seed robustness stress test for Gate 3.

Runs the SAME locked 15 application circuits against TWO historical fake IBM
backend snapshots. This follows inspection of Gate 3's initial result and
is explicitly POST-HOC: no new blinded/independent application corpus.
All compilers, logical checks and physical layouts are matched.
"""
from collections import Counter
from datetime import datetime, timezone
import argparse
import importlib.metadata
import json
from pathlib import Path

from benchmarks.gate3_applications import corpus, manifest
from benchmarks.gate3_noisy import (
    SHOTS, prob_from_counts, radius_bhc, noisy_counts,
    paired_status, sources, tvd,
)
from benchmarks.heldout_compare import prerequisites

SEEDS_FRESH = (20261120, 20261121)
BACKEND_NAMES = ("fake_manila", "fake_lagos")
N_CASES = 15
N_BASELINES = 3
FAMILYWISE_ALPHA = 0.05


def physical_operations(mapped):
    """Record actual physical qubit indices and operation order for auditing."""
    return [
        {"gate": item.operation.name,
         "physical_qubits": [mapped.find_bit(q).index for q in item.qubits],
         "classical_bits": [mapped.find_bit(c).index for c in item.clbits]}
        for item in mapped.data
    ]


def crossbackend():
    QuantumCircuit, transpile, qasm2, Operator, pyzx = prerequisites()
    from qiskit.quantum_info import Statevector
    from qiskit_aer import AerSimulator
    import qiskit_aer
    from qiskit_ibm_runtime.fake_provider import FakeManilaV2, FakeLagosV2

    if qiskit_aer.__version__ != "0.18.4":
        raise RuntimeError("unexpected Aer version")
    if len(corpus()) != N_CASES:
        raise RuntimeError("changed application manifest")
    models = (FakeManilaV2(), FakeLagosV2())
    result = {
        "schema": "physqed-q-gate3-crossbackend-posthoc-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "not_hardware_results": True,
        "not_current_calibrations": True,
        "posthoc_selection_notice":
            "Run after first Gate 3 result; same 15 authored circuits, fresh seeds and second historical fake backend",
        "original_first_result": "https://github.com/tonynewton79-web/PHYSQED-Q/actions/runs/44218561337",
        "manifest": manifest(), "seeds": list(SEEDS_FRESH),
        "shots_per_seed": SHOTS,
        "shots_per_candidate": SHOTS * len(SEEDS_FRESH),
        "backends": [],
    }
    # Familywise bound over 2 backends * 15 circuits * 3 compilers * 2
    # sampled distributions (noisy and noiseless native-routing controls).
    tests = len(models) * N_CASES * N_BASELINES * 2
    for backend in models:
        if backend.name not in BACKEND_NAMES:
            raise RuntimeError("unexpected backend identity")
        sim = AerSimulator.from_backend(backend, method="density_matrix")
        sim.set_options(max_parallel_threads=1)
        ideal_sim = AerSimulator(method="statevector", max_parallel_threads=1)
        props = backend.properties()
        section = {
            "backend": backend.name,
            "qubits": backend.num_qubits,
            "calibrated": str(props.last_update_date),
            "historical_snapshot": True,
            "cases": [],
        }
        total = Counter()
        for item in corpus():
            raw = item["circuit"]
            n = raw["qubits"]
            original, outputs, receipt, zx_t = sources(
                raw, QuantumCircuit, transpile, qasm2, Operator, pyzx)
            p = Statevector.from_instruction(original).probabilities()
            ideal = {format(i, f"0{n}b"):float(x) for i,x in enumerate(p)}
            rad = radius_bhc(2**n, SHOTS*len(SEEDS_FRESH),
                             tests, alpha=FAMILYWISE_ALPHA)
            row = {"name": item["name"], "family": item["family"],
                   "qubits": n, "compilers": {}, "comparisons": {}}
            for method in ("physqed", "qiskit", "pyzx"):
                measured = outputs[method].copy()
                measured.measure_all()
                mapped = transpile(
                    measured, backend=backend, optimization_level=3,
                    seed_transpiler=2026,
                    initial_layout=list(range(n)))
                ideal_counts = noisy_counts(ideal_sim, mapped, SHOTS, SEEDS_FRESH)
                ideal_dist = prob_from_counts(ideal_counts,n)
                if tvd(ideal,ideal_dist) > 0.10:
                    raise RuntimeError("noiseless mapped circuit failed")
                raw_counts = noisy_counts(sim,mapped,SHOTS,SEEDS_FRESH)
                d = tvd(prob_from_counts(raw_counts,n),ideal)
                gates = physical_operations(mapped)
                entry = {
                    "tvd": d, "sampling_radius": rad,
                    "native_two_qubit": sum(len(g["physical_qubits"])==2 for g in gates),
                    "native_cx_edges": [g["physical_qubits"] for g in gates
                                        if g["gate"]=="cx"],
                    "native_operations": gates,
                    "counts": dict(raw_counts),
                    "logical_operator_equivalence": True,
                    "exact_physqed_receipt": method=="physqed",
                    "original_physqed_receipt_hash": (
                        receipt["receipt_sha256"] if method=="physqed" else None),
                }
                if method=="pyzx":
                    entry["logical_t_count"]=zx_t
                row["compilers"][method]=entry
                total[method+"_cases"]+=1
            for comparator in ("qiskit","pyzx"):
                a=row["compilers"]["physqed"]["tvd"]
                b=row["compilers"][comparator]["tvd"]
                decision=paired_status(a,b,rad,rad)
                row["comparisons"][comparator]={
                    "phys_minus_comparator_tvd":a-b,
                    "decision":decision,"uncertainty_threshold":2*rad}
                total[comparator+"_"+decision]+=1
            section["cases"].append(row)
        section["summary"] = dict(sorted(total.items()))
        result["backends"].append(section)
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    r=crossbackend()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
    summary = [{
        "backend": b["backend"], "snapshot": b["calibrated"],
        "summary": b["summary"],
        "phase_cancel_n3": next(
            c["comparisons"]["pyzx"] for c in b["cases"]
            if c["name"]=="phase-cancel-n3")
    } for b in r["backends"]]
    print(json.dumps({
        "model_only":True, "posthoc":True, "manifest":r["manifest"]["sha256"],
        "backends":summary},indent=2,sort_keys=True))


if __name__=="__main__":
    main()
