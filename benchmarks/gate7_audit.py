"""Gate 7 data audit: independent routing/readout/TVD/aggregation replay.

No Aer/Qiskit physics recalculation; exact QASM source hashes are
separately checked before benchmarking. The auditor fails on omitted
refusals and records, altered output qubits, unaccounted native 2Q gates,
malformed physical SWAPs, inconsistent readout channels, or false wins.
"""
import argparse
import json
import math
from pathlib import Path
from benchmarks.gate7_qasmbench import SOURCE_BLOBS, COMMIT
from benchmarks.gate7_external_compare import SEEDS, OUTPUT_RULES
from benchmarks.gate6_executable_readout import BACKEND_IDS


def close(a,b,kind,tol=3e-8):
    if not math.isclose(float(a),float(b),rel_tol=0.,abs_tol=tol):
        raise RuntimeError(f"{kind}: {a} != {b}")


def vector(p,n):
    if not isinstance(p,dict):
        raise RuntimeError("no distribution")
    allowed={format(i,f"0{n}b") for i in range(1<<n)}
    if not set(p).issubset(allowed):
        raise RuntimeError("wrong distribution bit register")
    v=[float(p.get(format(i,f"0{n}b"),0.)) for i in range(1<<n)]
    if any(not math.isfinite(x) or x< -1e-10 for x in v):
        raise RuntimeError("bad output probability")
    close(sum(v),1.,"normalized probability",tol=3e-8)
    return v


def tvd(a,b):
    return .5*sum(abs(x-y) for x,y in zip(a,b))


def audit(doc):
    if doc.get("schema")!="physqed-q-gate7-external-qasmbench-v1":
        raise RuntimeError("unknown Gate 7 schema")
    if (doc["origin"]["upstream_commit"]!=COMMIT or
        doc["origin"]["source_file_count"]!=19 or
        doc.get("live_device_results") or
        not doc.get("all_19_sources_retrieved_and_sha1_verified") or
        not doc.get("no_synthetic_substitution") or
        doc.get("selected_by_result")):
        raise RuntimeError("incorrect source or provenance")
    declared={n:sha for n,sha in SOURCE_BLOBS}
    admissions=doc["admissions"]
    if len(admissions)!=19 or set(x["name"] for x in admissions)!=set(declared):
        raise RuntimeError("missing original external source/refusal")
    admitted=[x for x in admissions if x["admitted"]]
    if len(admitted)!=doc["accepted"] or len(admissions)-len(admitted)!=doc["refused"]:
        raise RuntimeError("unreconciled admission counts")
    for d in admissions:
        if d["source_git_blob_sha1"]!=declared[d["name"]]:
            raise RuntimeError("false frozen external source SHA")
        if d["admitted"] and ("reason" in d or "refusals" in d):
            raise RuntimeError("admitted unsupported source")
        if not d["admitted"] and not d.get("reason"):
            raise RuntimeError("silent refusal")
    if set(x["name"] for x in doc["benchmarks"])!=set(x["name"] for x in admitted):
        raise RuntimeError("substitution or omission of admitted source")
    if doc["qiskit_transpiler_seeds"]!=list(SEEDS) or doc["native_target_output_assignments"]!=list(OUTPUT_RULES):
        raise RuntimeError("seed/target specifications changed")
    checked=0
    computed_summary={}
    for record in doc["benchmarks"]:
        n=record["qubits"]
        target=vector(record["ideal_distribution"],n)
        if n not in (2,3,4) or len(record["backends"])!=2:
            raise RuntimeError("unexpected circuit width/backend count")
        if record["git_blob_sha1"]!=declared[record["name"]]:
            raise RuntimeError("file identity mismatch")
        for backend in record["backends"]:
            if backend["name"] not in BACKEND_IDS or len(backend["seed_runs"])!=len(SEEDS):
                raise RuntimeError("backend identity or missing seed")
            for seed_run,seed in zip(backend["seed_runs"],SEEDS):
                if seed_run["seed"]!=seed or set(seed_run["placements"])!=set(OUTPUT_RULES):
                    raise RuntimeError("missing seed/output allocation")
                for rule in OUTPUT_RULES:
                    slot=seed_run["placements"][rule]
                    goal=list(range(n)) if rule=="identity" else list(reversed(range(n)))
                    if slot["actual_common_physical_outputs"]!=goal:
                        raise RuntimeError("common output allocation changed")
                    if set(slot["methods"])!={"physqed","qiskit","pyzx"}:
                        raise RuntimeError("missing compiler")
                    for method,info in slot["methods"].items():
                        if not info["exact_full_operator_logical_check"]:
                            raise RuntimeError("logical unitary not checked")
                        if info["native_ideal_tvd"]>2e-7:
                            raise RuntimeError("native routing ideal state incorrect")
                        if info["native_physical_output_mapping"]!=goal:
                            raise RuntimeError("physical output mapping mismatched")
                        ledger=info["native_operations"]
                        measured={}
                        two=0
                        hist={}
                        for op in ledger:
                            nm=op["name"]
                            q=op["physical_qubits"]
                            cb=op["classical_bits"]
                            if nm=="measure":
                                if len(q)!=1 or len(cb)!=1 or cb[0] in measured:
                                    raise RuntimeError("invalid native readout")
                                measured[cb[0]]=q[0]
                            elif nm!="barrier":
                                hist[nm]=hist.get(nm,0)+1
                                if len(q)==2:two+=1
                        if [measured[i] for i in range(n)]!=goal:
                            raise RuntimeError("physical qubits of measured outputs not matched")
                        if hist!=info["native_operation_histogram"]:
                            raise RuntimeError("operation histogram incomplete")
                        if two!=info["native_two_qubit"]:
                            raise RuntimeError("native 2Q overhead omitted")
                        initial=info["native_initial_output_mapping"]
                        if len(initial)!=n or len(set(initial))!=n:
                            raise RuntimeError("invalid initial token mapping")
                        pos=list(initial)
                        for a,b in info["native_inserted_swaps"]:
                            pos=[b if q==a else a if q==b else q for q in pos]
                        if pos!=goal:
                            raise RuntimeError("inaccurate native SWAP routing trace")
                        if info["native_asap_seconds"]<0:
                            raise RuntimeError("invalid native duration")
                        gate=vector(info["gate_noise_probabilities"],n)
                        full=vector(info["full_probabilities"],n)
                        close(info["gate_noise_tvd"],tvd(gate,target),"gate TVD")
                        close(info["full_tvd"],tvd(full,target),"full TVD")
                        checked+=1
                    for baseline in ("qiskit","pyzx"):
                        a=slot["methods"]["physqed"]; b=slot["methods"][baseline]
                        expected={
                            "full_tvd_delta":a["full_tvd"]-b["full_tvd"],
                            "gate_tvd_delta":a["gate_noise_tvd"]-b["gate_noise_tvd"],
                            "two_qubit_delta":a["native_two_qubit"]-b["native_two_qubit"],
                            "asap_seconds_delta":a["native_asap_seconds"]-b["native_asap_seconds"]
                        }
                        for k,v in expected.items():
                            close(v,slot["contrasts"][baseline][k],"false signed delta")
    for backend in BACKEND_IDS:
        for rule in OUTPUT_RULES:
            for baseline in ("qiskit","pyzx"):
                for metric in ("full_tvd_delta","gate_tvd_delta","two_qubit_delta"):
                    values=[]
                    for item in doc["benchmarks"]:
                        b=next(z for z in item["backends"] if z["name"]==backend)
                        for seed in b["seed_runs"]:
                            values.append(seed["placements"][rule][
                                "contrasts"][baseline][metric])
                    key=f"{backend}.{rule}.{baseline}.{metric}"
                    expected={"phys_better":sum(x<-1e-7 for x in values),
                              "phys_equal":sum(abs(x)<=1e-7 for x in values),
                              "phys_worse":sum(x>1e-7 for x in values),
                              "n":len(values)}
                    if doc["summary"].get(key)!=expected:
                        raise RuntimeError("false aggregate results")
                    computed_summary[key]=expected
    expected_records=doc["accepted"]*len(BACKEND_IDS)*len(SEEDS)*len(OUTPUT_RULES)*3
    if checked!=expected_records:
        raise RuntimeError("missing complete matched-output comparisons")
    return {"schema":"physqed-q-gate7-independent-report-audit-v1",
            "status":"PASS","external_source_count":19,
            "admitted":doc["accepted"],"refused":doc["refused"],
            "native_candidate_records_audited":checked,
            "seed_repetitions":len(SEEDS),
            "real_hardware":False,
            "independent_physics_reimplementation":False}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("input",type=Path)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    result=audit(json.loads(args.input.read_text()))
    args.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print(json.dumps(result,sort_keys=True))


if __name__=="__main__":
    main()
