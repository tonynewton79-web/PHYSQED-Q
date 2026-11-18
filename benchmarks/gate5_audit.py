"""Independent arithmetic replay of Gate 5 archived-model counterfactuals.

This second pass uses its own bit-indexed readout channel implementation,
recomputed Gate 4 density-matrix evidence, and recomputes every stored
finite-shot summary from the complete per-trial raw metrics. This does
NOT independently verify Aer physics, backend calibration or hardware.
"""
import argparse
import json
import math
from pathlib import Path
import numpy as np
from benchmarks.gate4_noise_ablation import audit as source_audit


def table(m, assign, n):
    size=1 << n
    A=np.zeros((size,size))
    for t in range(size):
        for o in range(size):
            v=1.
            for c,q in enumerate(assign):
                v*=m[str(q)][(t>>c)&1][(o>>c)&1]
            A[o,t]=v
    return A


def vector(d,n):
    return np.array([d.get(format(i,f"0{n}b"),0.) for i in range(1<<n)])


def tvd(a,b):return float(np.sum(np.abs(a-b))/2.)


def close(a,b,label):
    if not math.isclose(float(a),float(b),rel_tol=0.,abs_tol=3e-8):
        raise RuntimeError(f"{label}: incorrect numeric result")


def validate(report):
    if (report.get("schema")!="physqed-q-gate5-readout-counterfactual-v1"
        or not report.get("posthoc") or report.get("live_hardware")
        or not report.get("matched_readout_is_nonexecutable_counterfactual")):
        raise RuntimeError("Gate 5 provenance invalid")
    raw=source_audit()
    if report["source_manifest"]!=raw["app_manifest"]["sha256"]:
        raise RuntimeError("source circuits changed")
    if len(report["backends"])!=len(raw["backends"]):
        raise RuntimeError("missing backend")
    validated=0
    trial_count=0
    for b, r in zip(raw["backends"],report["backends"]):
        if b["name"]!=r["name"] or len(b["cases"])!=len(r["cases"]):
            raise RuntimeError("historical backend/case mismatch")
        matrices=b["readout_calibration_by_physical_qubit"]
        for case,entry in zip(b["cases"],r["cases"]):
            if case["name"]!=entry["name"]:
                raise RuntimeError("case changed")
            n=case["qubits"]
            target=vector(case["ideal_target_probabilities"],n)
            original={}
            for name in ("physqed","qiskit","pyzx"):
                info=case["methods"][name]
                native=info["measurement_physical_qubits_for_classical_bits"]
                A=table(matrices,native,n)
                exact=vector(info["scenario_probabilities"]["calibrated_no_readout"],n)
                with_readout=vector(info["scenario_probabilities"]["calibrated_with_readout"],n)
                if np.max(np.abs(A@exact-with_readout))>3e-8:
                    raise RuntimeError("readout forward model does not reproduce history")
                original[name]=(A,exact,with_readout)
                if entry["methods"][name]["measurement_assignment"]!=native:
                    raise RuntimeError("readout physical assignment was altered")
            for name in original:
                A,p,full=original[name]
                expected={
                    "original_readout_tvd":tvd(full,target),
                    "gate_only_tvd":tvd(p,target),
                    "matched_phys_readout_tvd":tvd(original["physqed"][0]@p,target),
                    "matched_pyzx_readout_tvd":tvd(original["pyzx"][0]@p,target),
                    "nominal_inverted_tvd":tvd(np.linalg.solve(A,full),target),
                    "readout_condition_number":np.linalg.cond(A),
                }
                for k,value in expected.items():
                    close(value,entry["methods"][name][k], f"{b['name']} {case['name']} {name} {k}")
                    validated+=1
            for baseline in ("qiskit","pyzx"):
                for key,delta in entry["comparisons"][baseline].items():
                    close(delta,entry["methods"]["physqed"][key]-
                          entry["methods"][baseline][key],"signed contrast")
                    validated+=1
        trial=r["finite_shot_witness"]
        if trial["seed_start"]!=2026112201 or trial["number_of_repetitions"]!=50:
            raise RuntimeError("unexpected predeclared stochastic experiment")
        for method in ("physqed","pyzx"):
            for shots in ("8192","65536"):
                s=trial["methods"][method][shots]
                trials=s["trial_results"]
                if len(trials)!=50:
                    raise RuntimeError("incomplete finite-shot trial ledger")
                def med(k):
                    return float(np.median([z[k] for z in trials]))
                close(s["median_raw_tvd"],med("raw_tvd"),"median unmitigated")
                close(s["median_mitigated_tvd"],med("mitigated_tvd"),"median mitigated")
                close(s["p10_mitigated_tvd"],
                      np.percentile([z["mitigated_tvd"] for z in trials],10),"p10")
                close(s["p90_mitigated_tvd"],
                      np.percentile([z["mitigated_tvd"] for z in trials],90),"p90")
                close(s["fraction_negative_unconstrained"],
                      sum(z["negative_before_projection"] for z in trials)/50.,"negative frequency")
                trial_count+=50
    return {"schema":"physqed-q-gate5-secondpass-v1",
            "status":"PASS","audit_metric_checks":validated,
            "finite_shot_trial_results_checked":trial_count,
            "hardware_evidence":False,"physics_solver_independent":False}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("input",type=Path)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    report=validate(json.loads(a.input.read_text()))
    a.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps(report,sort_keys=True))


if __name__=="__main__":
    main()
