"""Gate 7: independently sourced held-out QASMBench and multiple Qiskit seeds.

Every source comes from the exact upstream PNNL Git blob frozen in
gate7_qasmbench.py. All 19 declared benchmarks are either admitted
strictly or explicitly refused with reasons. Never alter a circuit to
make it fit PHYSQED-Q. Only the admitted 2-4 qubit Clifford+T circuits
are compared in gate count, exact unitary and native executable
same-physical-output density-matrix error.

NO live QPU used. Historical 2024 FakeManila and FakeLagos ONLY.
"""
import argparse
import hashlib
import json
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone

from benchmarks.gate7_qasmbench import (
    SOURCE_BLOBS, inspect, manifest, read_source, acquire_sources
)
from benchmarks.gate3_noisy import sources
from benchmarks.gate6_executable_readout import (
    apply_route_and_native_compile, unmeasured_native_with_save,
    native_metrics, native_ledger, BACKEND_IDS,
)
from benchmarks.gate4_noise_ablation import (
    noise_scenarios, backend_readout_matrices,
    run_density_probabilities, apply_independent_readout,
)
from benchmarks.heldout_compare import (
    prerequisites, same_operator, logical_stats
)
from benchmarks.gate3_noisy import tvd

SEEDS=(2026, 2031, 2081)
OUTPUT_RULES=("identity","reverse")
GATE_BASIS=("h","x","z","s","sdg","t","tdg","cx","cz","swap")
VERIFICATION_TOL=2e-7


def gate_count(method, circuit, zx_t):
    data=logical_stats(circuit)
    if method=="pyzx":
        data["t_count"]=zx_t
    return data


def run(cache):
    QuantumCircuit, transpile, qasm2, Operator, pyzx=prerequisites()
    from qiskit.quantum_info import Statevector
    from qiskit_ibm_runtime.fake_provider import FakeManilaV2, FakeLagosV2
    admitted=[]
    decisions=[]
    for name, expected_sha in SOURCE_BLOBS:
        source=read_source(name,cache)
        result=inspect(name,source,qasm2)
        result["source_git_blob_sha1"]=expected_sha
        result["source_sha256"]=hashlib.sha256(source.encode("utf8")).hexdigest()
        decisions.append({key:value for key,value in result.items() if key!="logical"})
        if result["admitted"]:
            admitted.append(result)
    n_accepted=len(admitted)
    if len(decisions)!=19 or not n_accepted:
        raise RuntimeError("wrong input corpus or no supported external circuit")
    report={
        "schema":"physqed-q-gate7-external-qasmbench-v1",
        "created_utc":datetime.now(timezone.utc).isoformat(),
        "origin":manifest(),
        "admissions":decisions,
        "selected_by_result":False,
        "all_19_sources_retrieved_and_sha1_verified":True,
        "no_synthetic_substitution":True,
        "source_files_are_unmodified":True,
        "accepted":n_accepted,"refused":len(decisions)-n_accepted,
        "qiskit_transpiler_seeds":list(SEEDS),
        "native_target_output_assignments":list(OUTPUT_RULES),
        "backend_snapshots_are_historical_2024":True,
        "live_device_results":False,
        "baseline_pipeline":"Qiskit 2.6.1 opt3; PyZX 0.10.8 full_optimize plus Qiskit opt3 native mapping",
        "benchmarks":[],
    }
    for admitted_entry in admitted:
        raw=admitted_entry["logical"]
        n=raw["qubits"]
        # Full exact PHYSQED receipt verified inside sources() before use.
        original, candidates, receipt, zx_t=sources(
            raw,QuantumCircuit,transpile,qasm2,Operator,pyzx)
        ideal=Statevector.from_instruction(original).probabilities()
        ideal_distribution={
            format(k,f"0{n}b"):float(p) for k,p in enumerate(ideal)
        }
        rec={"name":admitted_entry["name"],
             "qubits":n,"git_blob_sha1":admitted_entry["source_git_blob_sha1"],
             "original_QASMBench_logical_gates":len(raw["gates"]),
             "original_qasm_source_sha256":decisions[
                 next(i for i,v in enumerate(decisions) if v["name"]==admitted_entry["name"])
             ]["source_sha256"],
             "physqed_exact_receipt_hash":receipt["receipt_sha256"],
             "ideal_distribution":ideal_distribution,
             "compiled_logical_t_counts":{
                 method:gate_count(method,candidates[method],zx_t)
                 for method in ("physqed","qiskit","pyzx")
             },
             "backends":[]}
        for backend in (FakeManilaV2(), FakeLagosV2()):
            if backend.name not in BACKEND_IDS:
                raise RuntimeError("unexpected backend")
            models,_=noise_scenarios(backend)
            matrix=backend_readout_matrices(backend)
            b={"name":backend.name,
               "last_calibration":str(backend.properties().last_update_date),
               "seed_runs":[]}
            for seed in SEEDS:
                # Qiskit compiler baseline varies the logical optimization
                # seed AS WELL AS the native mapping seed; PHYSQED and PyZX
                # logical outputs stay frozen while all three native
                # transpilers use the same current seed.
                qiskit_variant=transpile(
                    original,basis_gates=list(GATE_BASIS),
                    optimization_level=3,seed_transpiler=seed)
                if not same_operator(original,qiskit_variant,Operator):
                    raise RuntimeError("Qiskit logical multiseed operator failure")
                seed_outputs=dict(candidates)
                seed_outputs["qiskit"]=qiskit_variant
                row={"seed":seed,"placements":{}}
                native_front={}
                for method in ("physqed","qiskit","pyzx"):
                    candidate=seed_outputs[method].copy()
                    candidate.measure_all()
                    mapped=transpile(candidate,backend=backend,
                                     optimization_level=3,
                                     seed_transpiler=seed,
                                     initial_layout=list(range(n)))
                    if mapped.num_qubits!=backend.num_qubits:
                        raise RuntimeError("native physical width mismatch")
                    native_front[method]=mapped
                for rule in OUTPUT_RULES:
                    dst=tuple(range(n)) if rule=="identity" else tuple(
                        reversed(range(n)))
                    p={"actual_common_physical_outputs":list(dst),
                       "methods":{},"contrasts":{}}
                    for method in ("physqed","qiskit","pyzx"):
                        native,route=apply_route_and_native_compile(
                            native_front[method],n,dst,backend,transpile)
                        density,physical=unmeasured_native_with_save(native,n)
                        if physical!=list(dst):
                            raise RuntimeError("nonmatching physical measured outputs")
                        ideal_compiled=run_density_probabilities(density,None,n)
                        ideal_d=tvd(ideal_compiled,ideal_distribution)
                        if ideal_d>VERIFICATION_TOL:
                            raise RuntimeError("external source native circuit inequivalent")
                        gate=run_density_probabilities(
                            density,models["calibrated_no_readout"],n)
                        full=apply_independent_readout(gate,physical,matrix)
                        metrics=native_metrics(native,backend)
                        if metrics["missing_gate_durations"]:
                            raise RuntimeError("native durations absent")
                        p["methods"][method]={
                            "exact_full_operator_logical_check":True,
                            "native_ideal_tvd":ideal_d,
                            "native_two_qubit":metrics["native_two_qubit"],
                            "native_asap_seconds":metrics[
                                "native_asap_duration_without_readout_s"],
                            "native_operation_histogram":metrics["native_gate_counts"],
                            "native_physical_output_mapping":list(dst),
                            "native_initial_output_mapping":route["original_outputs"],
                            "native_inserted_swaps":route["physical_swaps"],
                            "native_operations":metrics["native_operations"],
                            "gate_noise_tvd":tvd(gate,ideal_distribution),
                            "full_tvd":tvd(full,ideal_distribution),
                            "gate_noise_probabilities":gate,
                            "full_probabilities":full,
                        }
                    for baseline in ("qiskit","pyzx"):
                        a=p["methods"]["physqed"]
                        c=p["methods"][baseline]
                        p["contrasts"][baseline]={
                            "full_tvd_delta":a["full_tvd"]-c["full_tvd"],
                            "gate_tvd_delta":a["gate_noise_tvd"]-c["gate_noise_tvd"],
                            "two_qubit_delta":a["native_two_qubit"]-c["native_two_qubit"],
                            "asap_seconds_delta":
                                a["native_asap_seconds"]-c["native_asap_seconds"],
                        }
                    row["placements"][rule]=p
                b["seed_runs"].append(row)
            rec["backends"].append(b)
        report["benchmarks"].append(rec)
    summary={}
    for backend in BACKEND_IDS:
        for rule in OUTPUT_RULES:
            for baseline in ("qiskit","pyzx"):
                for metric in ("full_tvd_delta","gate_tvd_delta","two_qubit_delta"):
                    values=[]
                    for item in report["benchmarks"]:
                        b=next(z for z in item["backends"] if z["name"]==backend)
                        for seed in b["seed_runs"]:
                            values.append(seed["placements"][rule][
                                "contrasts"][baseline][metric])
                    summary[f"{backend}.{rule}.{baseline}.{metric}"]={
                        "phys_better":sum(x < -1e-7 for x in values),
                        "phys_equal":sum(abs(x)<=1e-7 for x in values),
                        "phys_worse":sum(x > 1e-7 for x in values),
                        "n":len(values)}
    report["summary"]=summary
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source-dir",type=Path,required=True)
    p.add_argument("--download",action="store_true")
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    if args.download:
        acquire_sources(args.source_dir)
    data=run(args.source_dir)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(data,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"origin_commit":data["origin"]["upstream_commit"],
                      "accepted":data["accepted"],"refused":data["refused"],
                      "source_list":[
                          {"name":a["name"],"admitted":a["admitted"],
                           "reason":a.get("reason"),"refusals":a.get("refusals")}
                          for a in data["admissions"]],
                      "summary":data["summary"],
                      "not_real_hardware":True},sort_keys=True,indent=2))


if __name__=="__main__":
    main()
