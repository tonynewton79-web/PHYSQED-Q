"""Gate 6: executable common-physical-output comparison, historical model.

Unlike Gate 5, this test changes *native quantum circuits*, inserting
SWAP networks along valid backend couplings so all compiler candidates
measure the exact same specified physical output qubits. The additional
native 2Q operations and their errors ARE counted. These are executable
native-gate circuits on an archived fake backend target, not live runs.

Research provenance: post-hoc 5 selected synthetic application workloads,
two independent fixed output assignments (identity/reverse) per width.
No T-count superiority or actual superconducting improvement is claimed.
"""
import argparse
from collections import Counter, deque
from datetime import datetime, timezone
import json
from pathlib import Path

from benchmarks.gate3_applications import corpus, manifest
from benchmarks.gate3_noisy import sources, tvd
from benchmarks.gate4_noise_ablation import (
    apply_independent_readout, backend_readout_matrices,
    noise_scenarios, run_density_probabilities, unmeasured_native_with_save,
)
from benchmarks.heldout_compare import prerequisites

CASE_IDS=("phase-cancel-n3", "trotter-ising-n4", "ghz-n3",
          "qaoa-path-n3", "cluster-n3")
OUTPUT_RULES=("identity", "reverse")
BACKEND_IDS=("fake_manila", "fake_lagos")
METHODS=("physqed", "qiskit", "pyzx")
SEED_TRANSPILER=2026
IDEAL_TOL=2e-7


def coupling_edges(backend):
    """Undirected allowed CX adjacency, never assume long-range SWAPs."""
    if "cx" not in backend.target:
        raise RuntimeError("no supported native CX instruction")
    edges=set()
    for qpair, data in backend.target["cx"].items():
        if len(qpair) != 2 or qpair[0] == qpair[1]:
            raise RuntimeError("bad native coupling entry")
        a,b=sorted(qpair)
        if data is not None:
            edges.add((a,b))
    if not edges:
        raise RuntimeError("empty native connectivity")
    return tuple(sorted(edges))


def token_route(src, dst, edges):
    """Shortest number of native-neighbour SWAPs for tracked output tokens.

    src and dst are tuples of PHYSICAL locations indexed by classical bit.
    Unmeasured qubit locations are treated as movable unlabeled tokens.
    BFS is exact for nphysical<=7; no hand-optimized baseline routing.
    """
    src, dst = tuple(src), tuple(dst)
    n=len(src)
    if (n == 0 or n != len(dst) or len(set(src))!=n or
        len(set(dst))!=n or min(src+dst) < 0):
        raise ValueError("invalid output mapping")
    ordered=tuple(sorted(tuple(sorted(e)) for e in edges))
    if any(len(e)!=2 or e[0]==e[1] for e in ordered):
        raise ValueError("bad graph edge")
    all_physical=set(q for e in ordered for q in e)
    if not set(src+dst).issubset(all_physical):
        raise ValueError("output register outside connected device graph")
    if src == dst:
        return []
    queue=deque([src])
    seen={src:(None,None)}
    while queue:
        state=queue.popleft()
        for a,b in ordered:
            if a not in state and b not in state:
                continue
            after=tuple(b if pos==a else a if pos==b else pos for pos in state)
            if after in seen:
                continue
            seen[after]=(state,(a,b))
            if after==dst:
                output=[]
                cursor=after
                while seen[cursor][0] is not None:
                    prev,edge=seen[cursor]
                    output.append(edge)
                    cursor=prev
                output.reverse()
                return output
            queue.append(after)
    raise RuntimeError("no connected native physical SWAP route to outputs")


def derive_positions(native, n):
    """Extract authoritative final physical measurement destinations."""
    mapping={}
    for op in native.data:
        if op.operation.name != "measure":
            continue
        if len(op.clbits)!=1 or len(op.qubits)!=1:
            raise RuntimeError("malformed native measurement")
        cb=native.find_bit(op.clbits[0]).index
        qb=native.find_bit(op.qubits[0]).index
        if cb in mapping:
            raise RuntimeError("duplicate classical bit")
        mapping[cb]=qb
    if set(mapping)!=set(range(n)):
        raise RuntimeError("changed classical-bit mapping")
    found=tuple(mapping[i] for i in range(n))
    if len(set(found))!=n:
        raise RuntimeError("same output physical wire measured twice")
    return found


def apply_route_and_native_compile(native, n, dst, backend, transpile):
    """Preserve physical wire identities and append legal SWAP movements."""
    from qiskit import QuantumCircuit
    src=derive_positions(native,n)
    edges=coupling_edges(backend)
    route=token_route(src,dst,edges)
    phys_n=backend.num_qubits
    if native.num_qubits!=phys_n:
        raise RuntimeError("front-end native output is not full physical width")
    physical=QuantumCircuit(phys_n,n)
    seen_measure=False
    for item in native.data:
        if item.operation.name=="measure":
            seen_measure=True
            continue
        if item.operation.name=="barrier":
            continue
        if seen_measure:
            raise RuntimeError("unexpected post-measure quantum instruction")
        if item.clbits:
            raise RuntimeError("unsupported classical control in mapped candidate")
        qargs=[native.find_bit(q).index for q in item.qubits]
        physical.append(item.operation,[physical.qubits[q] for q in qargs])
    for a,b in route:
        if (min(a,b),max(a,b)) not in edges:
            raise RuntimeError("nonlocal SWAP inserted")
        physical.swap(a,b)
    for c,q in enumerate(dst):
        physical.measure(q,c)
    # Deliberately no optimiser freedom to change the output circuit layout.
    # Decompose adjacent SWAPs using the native backend Target, at level 0.
    routed=transpile(
        physical, backend=backend, initial_layout=list(range(phys_n)),
        layout_method="trivial", routing_method="basic",
        optimization_level=0, seed_transpiler=SEED_TRANSPILER
    )
    if derive_positions(routed,n)!=tuple(dst):
        raise RuntimeError("native backend transpilation moved measured outputs")
    return routed, {"original_outputs":list(src),
                    "required_outputs":list(dst),
                    "physical_swaps":[list(e) for e in route]}


def native_ledger(native):
    """Proof-carrying list of actual physical native operations."""
    result=[]
    for item in native.data:
        q=[native.find_bit(bit).index for bit in item.qubits]
        cl=[native.find_bit(bit).index for bit in item.clbits]
        result.append({"name":item.operation.name,"physical_qubits":q,
                       "classical_bits":cl})
    return result


def native_metrics(native, backend):
    ledger=native_ledger(native)
    gates=Counter(x["name"] for x in ledger if x["name"] not in ("measure","barrier"))
    native_2q=sum(len(x["physical_qubits"])==2 and x["name"]!="measure"
                  for x in ledger)
    duration_clocks=[0.]*backend.num_qubits
    missing=[]
    for op in ledger:
        name=op["name"]
        if name in ("measure","barrier"):
            continue
        q=tuple(op["physical_qubits"])
        instruction=backend.target.get(name,{}).get(q)
        if instruction is None or instruction.duration is None:
            missing.append({"name":name,"physical_qubits":list(q)})
            continue
        start=max((duration_clocks[k] for k in q),default=0.)
        for k in q:
            duration_clocks[k]=start+float(instruction.duration)
    return {"native_gate_counts":dict(sorted(gates.items())),
            "native_two_qubit":native_2q,
            "native_asap_duration_without_readout_s":
                (max(duration_clocks) if not missing else None),
            "missing_gate_durations":missing,
            "native_operations":ledger}


def compare():
    QuantumCircuit, transpile, qasm2, Operator, pyzx=prerequisites()
    from qiskit.quantum_info import Statevector
    from qiskit_ibm_runtime.fake_provider import FakeManilaV2, FakeLagosV2

    selected={r["name"]:r for r in corpus()}
    if not set(CASE_IDS).issubset(selected):
        raise RuntimeError("missing prespecified application circuits")
    results={
        "schema":"physqed-q-gate6-physical-common-readout-v1",
        "created_utc":datetime.now(timezone.utc).isoformat(),
        "source_manifest":manifest(),
        "posthoc_case_selection":True,
        "live_hardware":False,
        "virtual_native_compilation_only":True,
        "readout_placement_enforced_by_extra_native_swaps":True,
        "readout_mitigation_applied":False,
        "predeclared_cases":list(CASE_IDS),
        "predeclared_output_rules":list(OUTPUT_RULES),
        "backend_names":list(BACKEND_IDS),
        "backends":[],
    }
    for backend in (FakeManilaV2(),FakeLagosV2()):
        if backend.name not in BACKEND_IDS:
            raise RuntimeError("historical backend unexpected")
        noise,calibration=noise_scenarios(backend)
        readout_matrices=backend_readout_matrices(backend)
        edges=coupling_edges(backend)
        section={
            "name":backend.name,
            "historical_calibration_date":str(backend.properties().last_update_date),
            "physical_qubits":backend.num_qubits,
            "native_coupling_edges":[list(e) for e in edges],
            "readout_calibration_by_physical_qubit":readout_matrices,
            "cases":[],
        }
        for case_name in CASE_IDS:
            case=selected[case_name]
            raw=case["circuit"]
            width=raw["qubits"]
            original,outputs,receipt,zx_t=sources(
                raw,QuantumCircuit,transpile,qasm2,Operator,pyzx)
            v=Statevector.from_instruction(original).probabilities()
            ideal={format(i,f"0{width}b"):float(p) for i,p in enumerate(v)}
            row={"name":case_name,"n_logical_qubits":width,
                 "ideal_target_probs":ideal,
                 "physqed_exact_receipt_hash":receipt["receipt_sha256"],
                 "placements":{}}
            native_front={}
            for method in METHODS:
                logical=outputs[method].copy()
                logical.measure_all()
                candidate=transpile(
                    logical,backend=backend,optimization_level=3,
                    initial_layout=list(range(width)),
                    seed_transpiler=SEED_TRANSPILER)
                if candidate.num_qubits!=backend.num_qubits:
                    raise RuntimeError("backend physical width incompatible")
                native_front[method]=candidate
            for rule in OUTPUT_RULES:
                dst=tuple(range(width)) if rule=="identity" else tuple(
                    reversed(range(width)))
                trial={"required_physical_outputs":list(dst),
                       "candidate_methods":{},"contrasts":{}}
                for method in METHODS:
                    routed,mapping=apply_route_and_native_compile(
                        native_front[method],width,dst,backend,transpile)
                    analytic,output_pos=unmeasured_native_with_save(routed,width)
                    if output_pos!=list(dst):
                        raise RuntimeError("wrong real final measured-output placement")
                    p_ideal=run_density_probabilities(analytic,None,width)
                    if tvd(p_ideal,ideal) > IDEAL_TOL:
                        raise RuntimeError("native SWAP output not ideal equivalent")
                    p_gate=run_density_probabilities(
                        analytic,noise["calibrated_no_readout"],width)
                    p_full=apply_independent_readout(
                        p_gate,output_pos,readout_matrices)
                    metrics=native_metrics(routed,backend)
                    if metrics["missing_gate_durations"]:
                        raise RuntimeError("native gate duration missing")
                    trial["candidate_methods"][method]={
                        **mapping,**metrics,
                        "logical_operator_equivalence_checked":True,
                        "native_output_ideal_tvd":tvd(p_ideal,ideal),
                        "gate_only_tvd":tvd(p_gate,ideal),
                        "full_gate_and_matched_readout_tvd":tvd(p_full,ideal),
                        "gate_probabilities":p_gate,
                        "full_probabilities":p_full,
                    }
                for baseline in ("qiskit","pyzx"):
                    a=trial["candidate_methods"]["physqed"]
                    b=trial["candidate_methods"][baseline]
                    trial["contrasts"][baseline]={
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
                row["placements"][rule]=trial
            section["cases"].append(row)
        results["backends"].append(section)
    results["summary"]={}
    for b in results["backends"]:
        s={}
        for rule in OUTPUT_RULES:
            for baseline in ("qiskit","pyzx"):
                for metric in ("phys_minus_baseline_full_tvd",
                               "phys_minus_baseline_gate_only_tvd",
                               "phys_minus_baseline_native_two_qubit"):
                    deltas=[c["placements"][rule]["contrasts"][baseline][metric]
                            for c in b["cases"]]
                    s[f"{rule}_{baseline}_{metric}"]={
                        "phys_better":sum(x < -1e-7 for x in deltas),
                        "phys_equal":sum(abs(x)<=1e-7 for x in deltas),
                        "phys_worse":sum(x > 1e-7 for x in deltas),
                    }
        results["summary"][b["name"]]=s
    return results


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    report=compare()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    concise={
        b["name"]:{
            rule:{
                "phase_cancel_n3":next(
                    c for c in b["cases"] if c["name"]=="phase-cancel-n3"
                )["placements"][rule]["contrasts"]["pyzx"],
                "counts_vs_pyzx":report["summary"][b["name"]][
                    f"{rule}_pyzx_phys_minus_baseline_full_tvd"],
            } for rule in OUTPUT_RULES
        } for b in report["backends"]
    }
    print(json.dumps({"phase_manifest":manifest()["sha256"],
        "source":"archived backend; executable mapped circuits, not a hardware run",
        "cases_per_backend":len(CASE_IDS),
        "matched_placements":concise},indent=2,sort_keys=True))


if __name__=="__main__":
    main()
