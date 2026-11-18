"""Independent standard-library verification of stored Gate 4 numeric ledgers.

Recomputes every normalized ideal/noisy probability, TVD, contrast, native
CX path, and aggregate outcome without importing Qiskit, Aer, or PyZX.
Does not independently recompute physics or validate real hardware.
"""
import argparse
import json
import math
from pathlib import Path

from benchmarks.gate4_noise_ablation import CASES, SCENARIOS, BACKENDS, METHODS, TOL
from benchmarks.gate3_noisy import tvd


def close(a, b, label):
    if not math.isclose(a,b,rel_tol=0,abs_tol=2e-10):
        raise RuntimeError(f"{label} mismatch {a} vs {b}")


def probabilities(p,width):
    if not isinstance(p,dict) or not p:
        raise RuntimeError("empty probability")
    expected = {format(i, f"0{width}b") for i in range(1<<width)}
    if not set(p).issubset(expected):
        raise RuntimeError("nonstandard bitstring keys")
    if any(not math.isfinite(v) or v < -1e-12 for v in p.values()):
        raise RuntimeError("bad probability value")
    if abs(sum(p.values()) - 1.) > 2e-8:
        raise RuntimeError("distribution normalization differs beyond density-matrix tolerance")


def validate(report):
    if report.get("schema") != "physqed-q-gate4-deterministic-noise-causal-ablation-v1":
        raise RuntimeError("unknown research schema")
    if not report.get("posthoc_study") or report.get("live_hardware"):
        raise RuntimeError("invalid hardware/posthoc provenance")
    if report.get("predeclared_case_names") != list(CASES):
        raise RuntimeError("changed case selection")
    if report.get("predeclared_scenarios") != list(SCENARIOS):
        raise RuntimeError("changed noise scenarios")
    if len(report["backends"]) != len(BACKENDS):
        raise RuntimeError("missing backend")
    computed = {}
    key_summary = {}
    for backend in report["backends"]:
        name = backend["name"]
        if name not in BACKENDS or name in computed:
            raise RuntimeError("backend count/name incorrect")
        if len(backend["cases"]) != len(CASES):
            raise RuntimeError("missing experiment")
        observed = {}
        for row in backend["cases"]:
            case=row["name"]
            if case not in CASES or case in observed:
                raise RuntimeError("case missing/duplicate")
            observed[case]=True
            n=row["qubits"]
            target=row["ideal_target_probabilities"]
            probabilities(target,n)
            if set(row["methods"])!=set(METHODS):
                raise RuntimeError("missing compiler method")
            for method in METHODS:
                info=row["methods"][method]
                if not isinstance(info["native_operations"],list):
                    raise RuntimeError("no native ledger")
                measured=info["measurement_physical_qubits_for_classical_bits"]
                if len(measured)!=n or len(set(measured))!=n:
                    raise RuntimeError("bad physical output mapping")
                derived=[e["physical_qubits"] for e in info["native_operations"]
                         if e["name"]=="cx"]
                if derived!=info["native_cx_sequence"] or len(derived)!=info["cx_count"]:
                    raise RuntimeError("physical CNOT ledger mismatch")
                if set(info["scenario_tvd"])!=set(SCENARIOS):
                    raise RuntimeError("missing scenario TVD")
                if set(info["scenario_probabilities"])!=set(SCENARIOS):
                    raise RuntimeError("missing probability scenarios")
                for scenario in SCENARIOS:
                    p=info["scenario_probabilities"][scenario]
                    probabilities(p,n)
                    measured_tvd=tvd(p,target)
                    close(info["scenario_tvd"][scenario],measured_tvd,
                          f"{name} {case} {method} {scenario}")
                    if scenario=="ideal" and measured_tvd>TOL:
                        raise RuntimeError("noiseless unitary control failed")
            for comparator in ("qiskit","pyzx"):
                for scenario in SCENARIOS:
                    diff = row["methods"]["physqed"]["scenario_tvd"][scenario]-(
                        row["methods"][comparator]["scenario_tvd"][scenario])
                    claimed=row["contrasts"][comparator][scenario]
                    close(claimed["phys_minus_baseline_tvd"],diff,"pairwise contrast")
                    if claimed["phys_better_within_fixed_model"] != (diff < -TOL):
                        raise RuntimeError("misreported PHYSQED win")
                    if claimed["phys_worse_within_fixed_model"] != (diff > TOL):
                        raise RuntimeError("misreported PHYSQED loss")
        computed[name]=True
        key_summary[name] = {
            s:{base: {
                "phys_better": sum(r["contrasts"][base][s][
                    "phys_better_within_fixed_model"] for r in backend["cases"]),
                "phys_worse": sum(r["contrasts"][base][s][
                    "phys_worse_within_fixed_model"] for r in backend["cases"]),
                "approximately_equal": sum(
                    not (r["contrasts"][base][s]["phys_better_within_fixed_model"] or
                         r["contrasts"][base][s]["phys_worse_within_fixed_model"])
                    for r in backend["cases"])
            } for base in ("qiskit","pyzx")} for s in SCENARIOS}
        if report["summary"][name]!=key_summary[name]:
            raise RuntimeError("aggregate summary mismatch")
    if set(computed)!=set(BACKENDS):
        raise RuntimeError("wrong backends")
    return {
        "schema":"physqed-q-gate4-independent-numeric-audit-v1",
        "result":"PASS",
        "physics_model_independently_validated":False,
        "real_hardware_evidence":False,
        "backends":len(BACKENDS),
        "cases_per_backend":len(CASES),
        "candidates_per_case":len(METHODS),
        "scenarios_per_candidate":len(SCENARIOS),
        "recomputed_distributions":len(BACKENDS)*len(CASES)*len(METHODS)*len(SCENARIOS),
        "totals":key_summary,
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("input",type=Path)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    j=json.loads(a.input.read_text())
    result=validate(j)
    a.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({
        "status":"PASS", "recomputed":result["recomputed_distributions"],
        "evidence":"fixed-historical-model only"},sort_keys=True))


if __name__=="__main__":
    main()
