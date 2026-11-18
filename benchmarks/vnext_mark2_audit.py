"""Gate 9 / Mark II independent report-ledger auditor.

Reopens the original Git-SHA-pinned source files, recomputes exact QASM
admission decisions, independently calculates operation counts and
correlation-robust union upper bounds from native gate ledgers, and checks
all measured physical output positions and 2^n numerical full operators.

Uses the Mark II verifier for deterministic certificate replay; it is NOT
an independent formal prover, QPU experiment or authenticated calibration.
"""
import argparse
from fractions import Fraction
import json
from pathlib import Path

from benchmarks.gate7_qasmbench import SOURCE_BLOBS,read_source,COMMIT
from benchmarks.vnext_mark2_external import own_line_target,ROUTING_MODELS,OUTPUT_MODES
from physqed_q.vnext import VNextError
from physqed_q.vnext_qasm import strict_import
from physqed_q.vnext_mark2 import verify_mark2
from physqed_q.vnext_mark2_numeric import physical_operator_frobenius_error


def audit(document,source_dir):
    if (document.get("schema")!="physqed-q-vnext-mark2-original-external-routing-v1"
        or document.get("upstream_commit")!=COMMIT
        or document.get("no_live_hardware_executed") is not True
        or document.get("no_fake_processor_backend") is not True
        or document.get("target_model_provenance")!="synthetic"):
        raise RuntimeError("Mark II provenance not trustworthy")
    if len(document.get("cases",[]))!=19:
        raise RuntimeError("original published corpus truncated")
    checked=0
    total_swaps=0
    for (name,sha),row in zip(SOURCE_BLOBS,document["cases"]):
        if row["name"]!=name or row["upstream_blob_sha1"]!=sha:
            raise RuntimeError("published source hash/list changed")
        source=read_source(name,source_dir)
        try:
            info=strict_import(source,name="pnnl-"+name)
        except VNextError as exc:
            if row["admitted"] or row.get("refusal")!=str(exc):
                raise RuntimeError("source admission/refusal mismatch")
            continue
        if not row["admitted"]:
            raise RuntimeError("valid external source suppressed")
        if info["source_sha256"]!=row["original_qasm_source_sha256"]:
            raise RuntimeError("unmodified source sha256 mismatch")
        n=info["program"]["qubits"]
        if row["classical_output_bit_to_logical_qubit"]!=info[
            "classical_output_bit_to_quantum_qubit"]:
            raise RuntimeError("classical bit map changed")
        if set(row["placements"])!=set(ROUTING_MODELS):
            raise RuntimeError("target model omitted")
        for mode in ROUTING_MODELS:
            target,env=own_line_target(n,mode)
            if set(row["placements"][mode])!=set(OUTPUT_MODES):
                raise RuntimeError("output allocation omitted")
            for variant in OUTPUT_MODES:
                record=row["placements"][mode][variant]
                receipt=record["receipt"]
                verify_mark2(receipt)
                if (receipt["physical_target"]!=target or
                    receipt["physical_fault_envelope"]!=env):
                    raise RuntimeError("changed fixed physical target/fault assumptions")
                output=list(range(n)) if variant=="ascending" else list(
                    reversed(range(n)))
                if (record["required_physical_outputs"]!=output or
                    record["actual_physical_outputs"]!=output):
                    raise RuntimeError("nonidentical required/actual readout")
                if (receipt["source"]!=info["program"] or
                    receipt["classical_output_bit_to_logical_qubit"]!=
                    info["classical_output_bit_to_quantum_qubit"]):
                    raise RuntimeError("source or original measurement order changed")
                if [m["physical_qubit"] for m in
                        receipt["physical_output_measurements"]]!=output:
                    raise RuntimeError("native measurement mismatch")
                gates=receipt["native_circuit"]["gates"]
                count2=0
                cost=Fraction(0)
                edges={tuple(e[:2]):Fraction(e[2])
                       for e in env["two_qubit_fault_upper_by_edge"]}
                for g in gates:
                    qs=g["qubits"]
                    if len(qs)==2:
                        count2+=1
                        physical_edge=tuple(sorted(qs))
                        if physical_edge not in edges:
                            raise RuntimeError("nonlocal native instruction")
                        cost+=edges[physical_edge]
                    else:
                        cost+=Fraction(env["one_qubit_fault_upper"][qs[0]])
                for q in output:
                    cost+=Fraction(env["readout_fault_upper"][q])
                if count2!=record["physical_native_two_qubit"]:
                    raise RuntimeError("falsely reported two-qubit gate count")
                if len(gates)!=record["physical_native_gates"]:
                    raise RuntimeError("falsely reported total physical native gates")
                if len(receipt["routing_swap_ledger"])!=record[
                    "inserted_routing_swaps"]:
                    raise RuntimeError("hidden inserted physical SWAPs")
                if str(min(Fraction(1),cost))!=record[
                    "marginal_fault_tvd_upper"]:
                    raise RuntimeError("correlated marginal noise bound falsified")
                imported=Fraction(info["source_to_rationalpi_projective_bound"])
                expected=imported+Fraction(receipt["logical_projective_operator_bound"])
                if str(expected)!=record["original_qasm_to_routed_projective_upper"]:
                    raise RuntimeError("original decimal QASM error bound omitted")
                numeric=physical_operator_frobenius_error(receipt)
                if abs(numeric-record[
                    "independent_full_operator_frobenius_error"])>1e-11:
                    raise RuntimeError("full physical operator matrix audit falsified")
                if numeric>2e-9:
                    raise RuntimeError("native operator not equal to source up to routing")
                total_swaps+=record["inserted_routing_swaps"]
                checked+=1
    if (document["admitted"]!=15 or document["refused"]!=4 or
        checked!=60 or document["routed_native_circuits"]!=60):
        raise RuntimeError("incomplete external Mark II corpus")
    return {"schema":"physqed-q-vnext-mark2-independent-ledger-audit-v1",
            "status":"PASS",
            "pinned_original_published_sources":19,
            "source_programs_supported":15,
            "source_programs_explicitly_refused":4,
            "native_full_operator_certificates_replayed":checked,
            "total_inserted_swaps_across_test_matrix":total_swaps,
            "hardware_executions":0,"fake_backend_used":False,
            "formal_independent_proof_checker":False}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("input",type=Path)
    p.add_argument("--sources",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    out=audit(json.loads(args.input.read_text()),args.sources)
    args.output.write_text(json.dumps(out,sort_keys=True,indent=2)+"\n")
    print(json.dumps(out,sort_keys=True,indent=2))


if __name__=="__main__":
    main()
