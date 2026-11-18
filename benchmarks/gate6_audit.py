"""Independent data-level Gate 6 audit, without using Aer or Qiskit.

Checks native measured physical output constraints, full physical operation
ledgers, local couplings, explicit routing token trace, probability
normalization, classical readout remapping, TVD and all summary counts.

Does not independently solve quantum dynamics or verify device calibrations.
"""
import argparse
import json
import math
from pathlib import Path


BACKENDS=("fake_manila","fake_lagos")
RULES=("identity","reverse")
METHODS=("physqed","qiskit","pyzx")
CASES=("phase-cancel-n3","trotter-ising-n4","ghz-n3",
       "qaoa-path-n3","cluster-n3")


def close(a,b,description,eps=3e-8):
    if not math.isclose(float(a),float(b),abs_tol=eps,rel_tol=0.):
        raise RuntimeError(description+f" {a} != {b}")


def to_probability_vector(p,n):
    if not isinstance(p,dict):
        raise RuntimeError("missing density-matrix probability output")
    allowed={format(k,f"0{n}b") for k in range(1<<n)}
    if not set(p).issubset(allowed):
        raise RuntimeError("unexpected probability bit ordering")
    arr=[float(p.get(format(k,f"0{n}b"),0)) for k in range(1<<n)]
    if any(x < -1e-10 or not math.isfinite(x) for x in arr):
        raise RuntimeError("invalid probabilities")
    close(sum(arr),1.,"probability normalization",eps=3e-8)
    return arr


def readout_replay(pre, bit_to_physical, confusion):
    n=len(bit_to_physical)
    out=[0.]*(1<<n)
    for original,p in enumerate(pre):
        for observed in range(1<<n):
            likelihood=p
            for c,q in enumerate(bit_to_physical):
                matrix=confusion[str(q)]
                likelihood*=matrix[(original>>c)&1][(observed>>c)&1]
            out[observed]+=likelihood
    return out


def tvd(a,b):
    return sum(abs(p-q) for p,q in zip(a,b)) / 2.


def validate(document):
    if (document.get("schema")!="physqed-q-gate6-physical-common-readout-v1"
        or document.get("live_hardware")
        or not document.get("posthoc_case_selection")
        or not document.get("readout_placement_enforced_by_extra_native_swaps")):
        raise RuntimeError("provenance mismatch")
    if (document["predeclared_cases"] != list(CASES) or
        document["predeclared_output_rules"] != list(RULES) or
        document["backend_names"] != list(BACKENDS)):
        raise RuntimeError("cases/backend changed or selected after result")
    if len(document["backends"])!=2:
        raise RuntimeError("wrong historical backend count")
    checked=0
    summary={}
    for backend in document["backends"]:
        name=backend["name"]
        if name not in BACKENDS or name in summary or len(backend["cases"])!=5:
            raise RuntimeError("unexpected or repeated backend/cases")
        edges={tuple(sorted(q)) for q in backend["native_coupling_edges"]}
        if not edges:
            raise RuntimeError("native coupling set empty")
        classical_matrix=backend["readout_calibration_by_physical_qubit"]
        section={}
        cases_seen=set()
        for row in backend["cases"]:
            cid=row["name"]
            if cid not in CASES or cid in cases_seen:
                raise RuntimeError("unexpected or duplicate circuit")
            cases_seen.add(cid)
            n=row["n_logical_qubits"]
            target=to_probability_vector(row["ideal_target_probs"],n)
            if set(row["placements"])!=set(RULES):
                raise RuntimeError("output placement omitted")
            for rule in RULES:
                entry=row["placements"][rule]
                goal=list(range(n)) if rule=="identity" else list(reversed(range(n)))
                if entry["required_physical_outputs"]!=goal:
                    raise RuntimeError("output mapping changed from preregistered target")
                if set(entry["candidate_methods"])!=set(METHODS):
                    raise RuntimeError("missing candidate")
                for method,info in entry["candidate_methods"].items():
                    if info["required_outputs"]!=goal:
                        raise RuntimeError("method route goal incorrect")
                    state=list(info["original_outputs"])
                    if len(state)!=n or len(set(state))!=n:
                        raise RuntimeError("invalid original output mapping")
                    for swap in info["physical_swaps"]:
                        a,b=swap
                        if tuple(sorted((a,b))) not in edges:
                            raise RuntimeError("nonlocal physical SWAP")
                        state=[b if q==a else a if q==b else q for q in state]
                    if state!=goal:
                        raise RuntimeError("claimed SWAP trace fails")
                    physical_reads={}
                    twoq=0
                    for op in info["native_operations"]:
                        op_name=op["name"]
                        qubits=op["physical_qubits"]
                        classical=op["classical_bits"]
                        if op_name=="measure":
                            if len(qubits)!=1 or len(classical)!=1:
                                raise RuntimeError("nonstandard mapped readout")
                            bit=classical[0]
                            if bit in physical_reads:
                                raise RuntimeError("repeated output classical bit")
                            physical_reads[bit]=qubits[0]
                        elif op_name!="barrier" and len(qubits)==2:
                            twoq+=1
                            if tuple(sorted(qubits)) not in edges:
                                raise RuntimeError("nonlocal two-qubit native gate")
                    if [physical_reads[k] for k in range(n)]!=goal:
                        raise RuntimeError("physically measured outputs do not match")
                    if info["native_two_qubit"]!=twoq:
                        raise RuntimeError("underreported native two-qubit count")
                    if (info["missing_gate_durations"] or
                        info["native_asap_duration_without_readout_s"] is None):
                        raise RuntimeError("incomplete native cost record")
                    gate=to_probability_vector(info["gate_probabilities"],n)
                    full=to_probability_vector(info["full_probabilities"],n)
                    reconstructed=readout_replay(gate,goal,classical_matrix)
                    for lhs,rhs in zip(reconstructed,full):
                        close(lhs,rhs,"classical readout operator mismatch")
                    close(info["gate_only_tvd"],tvd(gate,target),"gate-only TVD")
                    close(info["full_gate_and_matched_readout_tvd"],
                          tvd(full,target),"native full TVD")
                    if info["native_output_ideal_tvd"] > 2e-7:
                        raise RuntimeError("reported ideal native unitary failure")
                    checked+=1
                for base in ("qiskit","pyzx"):
                    a=entry["candidate_methods"]["physqed"]
                    b=entry["candidate_methods"][base]
                    delta={
                        "phys_minus_baseline_gate_only_tvd":
                            a["gate_only_tvd"]-b["gate_only_tvd"],
                        "phys_minus_baseline_full_tvd":
                            a["full_gate_and_matched_readout_tvd"]-
                            b["full_gate_and_matched_readout_tvd"],
                        "phys_minus_baseline_native_two_qubit":
                            a["native_two_qubit"]-b["native_two_qubit"],
                        "phys_minus_baseline_native_asap_seconds":
                            a["native_asap_duration_without_readout_s"]-
                            b["native_asap_duration_without_readout_s"],
                    }
                    for k,value in delta.items():
                        close(value,entry["contrasts"][base][k],
                              "incorrect signed physical comparison")
        if cases_seen!=set(CASES):
            raise RuntimeError("missing prespecified circuits")
        for rule in RULES:
            for base in ("qiskit","pyzx"):
                for metric in ("phys_minus_baseline_full_tvd",
                               "phys_minus_baseline_gate_only_tvd",
                               "phys_minus_baseline_native_two_qubit"):
                    deltas=[c["placements"][rule]["contrasts"][base][metric]
                            for c in backend["cases"]]
                    key=f"{rule}_{base}_{metric}"
                    expected={"phys_better":sum(x < -1e-7 for x in deltas),
                              "phys_equal":sum(abs(x)<=1e-7 for x in deltas),
                              "phys_worse":sum(x > 1e-7 for x in deltas)}
                    if document["summary"][name][key]!=expected:
                        raise RuntimeError("incorrect aggregate comparison")
                    section[key]=expected
        summary[name]=section
    if set(summary)!=set(BACKENDS) or checked!=60:
        raise RuntimeError("incomplete 60 native candidate circuits")
    return {"schema":"physqed-q-gate6-independent-ledger-audit-v1",
            "status":"PASS",
            "routed_candidates_audited":checked,
            "posthoc":True,"hardware_measurements":False,
            "independently_recomputed_quantum_dynamics":False}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("input",type=Path)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    result=validate(json.loads(args.input.read_text()))
    args.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print(json.dumps(result,sort_keys=True))


if __name__=="__main__":
    main()
