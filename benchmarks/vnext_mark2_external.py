"""Mark II own-router replay on all 19 pinned PNNL QASMBench QASM files.

The 15 accepted vNext Alpha circuits are physically routed to two
different device-independent line-target models:
(1) native SWAP, (2) bidirectional CNOT with exact 3-CNOT SWAP.
Each uses two forced measured-output permutations. 15*2*2 = 60
native routes are verified with the separate dense 2^n operator oracle.

No IBM historical fake device, Qiskit, Aer, PyZX, QPU, or measured
device calibration. The synthetic edge/qubit faults are examples,
not empirical hardware accuracy predictions.
"""
import argparse
from datetime import datetime,timezone
from fractions import Fraction
import json
from pathlib import Path

from benchmarks.gate7_qasmbench import (
    SOURCE_BLOBS,read_source,acquire_sources,COMMIT
)
from physqed_q.vnext import VNextError
from physqed_q.vnext_qasm import strict_import
from physqed_q.vnext_mark2 import compile_mark2,verify_mark2
from physqed_q.vnext_mark2_numeric import physical_operator_frobenius_error

ROUTING_MODELS=("native_swap","three_cnot_swap")
OUTPUT_MODES=("ascending","reversed")
MATRIX_TOL=2e-9


def own_line_target(n, mode):
    if mode not in ROUTING_MODELS or not 2<=n<=4:
        raise VNextError("invalid independent Mark II target")
    couplings=[[i,i+1] for i in range(n-1)]
    gates=["H","X","Z","S","SDG","T","TDG",
           "RZPI","CNOT","CZ"]
    if mode=="native_swap":
        gates.append("SWAP")
    target={
        "name":"OWN_DECLARED_"+str(n)+"Q_LINE_"+mode.upper(),
        "qubits":n,"native_gates":sorted(gates),
        "couplings":couplings,
        "one_qubit_fault":"0","two_qubit_fault":"0",
        "readout_faults":["0"]*n,"provenance":"synthetic",
    }
    # Distinct rational fault ceilings for each physical qubit and edge.
    # No independence is required for the marginal union upper bound.
    model={
        "one_qubit_fault_upper":[str(Fraction(1,1000+100*i))
                                 for i in range(n)],
        "two_qubit_fault_upper_by_edge":[
            [a,b,str(Fraction(1,200+50*a))] for a,b in couplings],
        "readout_fault_upper":[str(Fraction(1,50+10*i))
                               for i in range(n)],
        "fault_semantics":"marginal_fault_event_upper_bounds",
        "provenance":"synthetic",
    }
    return target,model


def compare(folder):
    report={
        "schema":"physqed-q-vnext-mark2-original-external-routing-v1",
        "created_utc":datetime.now(timezone.utc).isoformat(),
        "published_corpus":"PNNL QASMBench pinned Git blobs",
        "upstream_commit":COMMIT,
        "original_source_count":len(SOURCE_BLOBS),
        "target_model_provenance":"synthetic",
        "no_fake_processor_backend":True,
        "no_qiskit_pyzx_or_aer_used":True,
        "no_live_hardware_executed":True,
        "routing_local_not_global_optimum":True,
        "external_admission_retrospective_not_blind":True,
        "models":list(ROUTING_MODELS),
        "output_allocations":list(OUTPUT_MODES),
        "cases":[],
    }
    for name,sha in SOURCE_BLOBS:
        qasm=read_source(name,folder)
        row={"name":name,"upstream_blob_sha1":sha,"admitted":False}
        try:
            imported=strict_import(qasm,name="pnnl-"+name)
            program=imported["program"]
            n=program["qubits"]
            if n<2:
                raise VNextError("Mark II external test minimum width 2")
            row["admitted"]=True
            row["original_qasm_source_sha256"]=imported["source_sha256"]
            row["classical_output_bit_to_logical_qubit"]=(
                imported["classical_output_bit_to_quantum_qubit"])
            row["original_qasm_import_bound"]=(
                imported["source_to_rationalpi_projective_bound"])
            row["placements"]={}
            for mode in ROUTING_MODELS:
                target,envelope=own_line_target(n,mode)
                per_mode={}
                for rule in OUTPUT_MODES:
                    output=(list(range(n)) if rule=="ascending"
                            else list(reversed(range(n))))
                    receipt=compile_mark2(
                        program,target,envelope,
                        classical_output_bit_to_logical_qubit=(
                            imported["classical_output_bit_to_quantum_qubit"]),
                        required_physical_qubits_for_classical_bits=output,
                        max_projective_error="0")
                    verify_mark2(receipt)
                    discrepancy=physical_operator_frobenius_error(receipt)
                    if discrepancy>MATRIX_TOL:
                        raise RuntimeError(
                            f"FULL_PHYSICAL_OPERATOR_FAILURE {name} {mode} {rule}: "
                            f"{discrepancy}")
                    import_error=Fraction(
                        imported["source_to_rationalpi_projective_bound"])
                    logical_error=Fraction(
                        receipt["logical_projective_operator_bound"])
                    end_to_end_error=import_error+logical_error
                    if end_to_end_error>Fraction(1,1000000):
                        raise RuntimeError("original-QASM import error unbounded")
                    per_mode[rule]={
                        "required_physical_outputs":output,
                        "actual_physical_outputs":[
                            m["physical_qubit"]
                            for m in receipt["physical_output_measurements"]],
                        "physical_native_gates":receipt["cost"]["physical_native_gates"],
                        "physical_native_two_qubit":receipt["cost"][
                            "physical_native_two_qubit"],
                        "inserted_routing_swaps":receipt["cost"]["inserted_local_swaps"],
                        "native_unit_weight_depth":receipt["cost"][
                            "native_depth_unit_weight"],
                        "marginal_fault_tvd_upper":receipt[
                            "correlation_robust_marginal_fault_union_bound"],
                        "original_qasm_to_routed_projective_upper":str(end_to_end_error),
                        "independent_full_operator_frobenius_error":discrepancy,
                        "receipt":receipt,
                    }
                row["placements"][mode]=per_mode
        except VNextError as exc:
            if row["admitted"]:
                raise RuntimeError(
                    "previously admissible vNext Alpha external circuit "
                    f"failed Mark II routing: {name}, {exc}") from exc
            row["refusal"]=str(exc)
        report["cases"].append(row)
    report["admitted"]=sum(x["admitted"] for x in report["cases"])
    report["refused"]=len(report["cases"])-report["admitted"]
    report["routed_native_circuits"]=report["admitted"]*len(ROUTING_MODELS)*len(OUTPUT_MODES)
    if report["admitted"]!=15 or report["routed_native_circuits"]!=60:
        raise RuntimeError("fixed external corpus coverage changed")
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--sources",type=Path,required=True)
    p.add_argument("--download",action="store_true")
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    if args.download:
        acquire_sources(args.sources)
    report=compare(args.sources)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    summary=[]
    for row in report["cases"]:
        if not row["admitted"]:
            summary.append({"name":row["name"],"accepted":False,
                            "refusal":row["refusal"]})
        else:
            details=row["placements"]
            summary.append({"name":row["name"],"accepted":True,
                "ascending_native_swap_2q":
                    details["native_swap"]["ascending"]["physical_native_two_qubit"],
                "ascending_3cnot_swap_2q":
                    details["three_cnot_swap"]["ascending"]["physical_native_two_qubit"],
                "ascending_native_swap_error_ceiling":
                    details["native_swap"]["ascending"]["marginal_fault_tvd_upper"]})
    print(json.dumps({
        "source_revisions_verified":len(SOURCE_BLOBS),
        "accepted":report["admitted"],"refused":report["refused"],
        "physically_routed_certificates":report["routed_native_circuits"],
        "device_type":"own declared synthetic line, not hardware",
        "cases":summary},indent=2,sort_keys=True))


if __name__=="__main__":
    main()
