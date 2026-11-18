"""Gate 5: matched classical readout channels and nominal readout mitigation.

POST-HOC. Recompute Gate 4's FIXED historical, synthetic density matrices.
Equalising classical readout channels does NOT reroute or physically execute
a different native circuit. It is a controlled counterfactual of
measurement assignment, not an apples-to-apples real-hardware experiment.

The analytic inversion knows exact historical readout error parameters:
neither live calibration uncertainty nor drift is represented.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np
from benchmarks.gate4_noise_ablation import audit as gate4_audit

SHOTS = (8192, 65536)
REPS = 50
SEED_START = 2026112201
METHODS = ("physqed", "qiskit", "pyzx")
EPS = 2.e-8


def probs(data, n):
    values = np.array([float(data.get(format(i, f"0{n}b"), 0.))
                       for i in range(2 ** n)], dtype=float)
    if np.any(values < -EPS) or abs(np.sum(values)-1.) > EPS:
        raise RuntimeError("invalid probability distribution")
    return values


def readout_channel(matrices, physical_assignment):
    """Column-stochastic M[observed, true], with bit 0 least significant."""
    one = [np.array(matrices[str(q)], dtype=float).T for q in physical_assignment]
    M = one[-1]
    for matrix in one[-2::-1]:
        M = np.kron(M, matrix)
    if not np.allclose(M.sum(axis=0), 1., rtol=0., atol=EPS):
        raise RuntimeError("readout matrix not column stochastic")
    if np.linalg.cond(M) > 1e6:
        raise RuntimeError("refuse near-singular naive readout inversion")
    return M


def tvd(p, q):
    return float(np.abs(p-q).sum() / 2.)


def simplex_projection(vector):
    """Euclidean projection onto nonnegative probabilities summing to one."""
    u = np.sort(vector)[::-1]
    rho_candidates = np.nonzero(
        u-(np.cumsum(u)-1.) / np.arange(1, len(u)+1) > 0.
    )[0]
    if len(rho_candidates)==0:
        raise RuntimeError("simplex projection failed")
    rho = rho_candidates[-1]
    tau = (np.sum(u[:rho+1])-1.)/(rho+1.)
    output = np.maximum(vector-tau, 0.)
    if not np.allclose(output.sum(),1.,atol=EPS,rtol=0.):
        raise RuntimeError("simplex normalization failed")
    return output


def shot_study(backend_id, item):
    """Independent fixed-seed multinomial draws of *archived model*."""
    if item["name"] != "phase-cancel-n3":
        raise RuntimeError("only preregistered witness supports finite-shot study")
    n=item["qubits"]
    target=probs(item["ideal_target_probabilities"],n)
    matrices=item["_readout_calibration"]
    answer={"number_of_repetitions":REPS, "seed_start":SEED_START,
            "shots":list(SHOTS), "methods":{}}
    for method_id, method in enumerate(("physqed","pyzx")):
        src=item["methods"][method]
        M=readout_channel(matrices,src["measurement_physical_qubits_for_classical_bits"])
        p=probs(src["scenario_probabilities"]["calibrated_with_readout"],n)
        series={}
        for N in SHOTS:
            records=[]
            for k in range(REPS):
                seed=np.random.SeedSequence([SEED_START+k, backend_id, method_id, N])
                rng=np.random.default_rng(seed)
                empirical=rng.multinomial(N,p/p.sum())/N
                inv=np.linalg.solve(M,empirical)
                projected=simplex_projection(inv)
                records.append({
                    "raw_tvd":tvd(empirical,target),
                    "mitigated_tvd":tvd(projected,target),
                    "negative_before_projection":bool(np.any(inv < -1.e-10)),
                })
            series[str(N)]={
                "median_raw_tvd":float(np.median([r["raw_tvd"] for r in records])),
                "median_mitigated_tvd":float(np.median(
                    [r["mitigated_tvd"] for r in records])),
                "p10_mitigated_tvd":float(np.percentile(
                    [r["mitigated_tvd"] for r in records],10)),
                "p90_mitigated_tvd":float(np.percentile(
                    [r["mitigated_tvd"] for r in records],90)),
                "fraction_negative_unconstrained":float(np.mean(
                    [r["negative_before_projection"] for r in records])),
            }
        answer["methods"][method]=series
    return answer


def evaluate():
    source=gate4_audit()  # independently regenerates the frozen 270 Gate 4 outputs
    result={
        "schema":"physqed-q-gate5-readout-counterfactual-v1",
        "created_utc":datetime.now(timezone.utc).isoformat(),
        "source_manifest":source["app_manifest"]["sha256"],
        "source_gate4_schema":source["schema"],
        "posthoc":True,
        "live_hardware":False,
        "calibration_uncertainty_included":False,
        "matched_readout_is_nonexecutable_counterfactual":True,
        "readout_inversion_uses_exact_known_model_parameters":True,
        "finite_shot_model_only":True,
        "backends":[],
    }
    for backend_id,b in enumerate(source["backends"]):
        out={"name":b["name"],"historical_calibration":b["historical_calibration_time"],
             "cases":[], "finite_shot_witness":None}
        matrices=b["readout_calibration_by_physical_qubit"]
        for case in b["cases"]:
            n=case["qubits"]
            target=probs(case["ideal_target_probabilities"],n)
            fixed={}
            for name in METHODS:
                info=case["methods"][name]
                M=readout_channel(matrices,
                    info["measurement_physical_qubits_for_classical_bits"])
                full=probs(info["scenario_probabilities"]["calibrated_with_readout"],n)
                gate=probs(info["scenario_probabilities"]["calibrated_no_readout"],n)
                if np.max(np.abs(M@gate-full))>1e-9:
                    raise RuntimeError("gate+readout distribution replay failed")
                inverse=np.linalg.solve(M,full)
                if np.max(np.abs(inverse-gate))>1e-8:
                    raise RuntimeError("analytical readout inversion not accurate")
                fixed[name]={"gate":gate,"full":full,"M":M,"inverse":inverse,
                    "native_assignment":
                      info["measurement_physical_qubits_for_classical_bits"]}
            M_phys=fixed["physqed"]["M"]; M_pyzx=fixed["pyzx"]["M"]
            record={"name":case["name"],"family":case["name"].rsplit("-n",1)[0],
                    "qubits":n,"methods":{}, "comparisons":{}}
            keys=("original_readout_tvd","gate_only_tvd",
                  "matched_phys_readout_tvd","matched_pyzx_readout_tvd",
                  "nominal_inverted_tvd")
            for name in METHODS:
                info=fixed[name]
                record["methods"][name]={
                    "measurement_assignment":info["native_assignment"],
                    "readout_condition_number":float(np.linalg.cond(info["M"])),
                    "original_readout_tvd":tvd(info["full"],target),
                    "gate_only_tvd":tvd(info["gate"],target),
                    "matched_phys_readout_tvd":tvd(M_phys@info["gate"],target),
                    "matched_pyzx_readout_tvd":tvd(M_pyzx@info["gate"],target),
                    "nominal_inverted_tvd":tvd(info["inverse"],target),
                }
            for comp in ("qiskit","pyzx"):
                record["comparisons"][comp]={
                    key:record["methods"]["physqed"][key]-
                        record["methods"][comp][key] for key in keys
                }
            out["cases"].append(record)
            if case["name"]=="phase-cancel-n3":
                case_with_calib={**case,"_readout_calibration":matrices}
                out["finite_shot_witness"]=shot_study(backend_id,case_with_calib)
        result["backends"].append(out)
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    report=evaluate()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    concise={}
    for b in report["backends"]:
        witness=next(c for c in b["cases"] if c["name"]=="phase-cancel-n3")
        concise[b["name"]]={
            "phase_cancel_n3_phys_minus_pyzx":witness["comparisons"]["pyzx"],
            "phase_cancel_n3_finite_shot":b["finite_shot_witness"],
            "total_application_cases":len(b["cases"])}
    print(json.dumps({"status":"SIMULATOR_COUNTERFACTUAL_ONLY",
        "manifest":report["source_manifest"],"results":concise},indent=2,sort_keys=True))


if __name__=="__main__":
    main()
