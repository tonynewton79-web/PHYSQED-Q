"""Gate 8 / vNext: unmodified external PNNL QASMBench source admission.

All 19 frozen original QASM source blobs from the prior Gate 7 manifest
are retrieved and verified. This time the compiler AND front-end are
owned by PHYSQED-Q, not Qiskit or PyZX. This is an explicitly post-hoc
capability extension against the known Gate 7 refusals.

"exact native" means exact mathematical RZPI under a declared TARGET,
not a fabricated physical rotation or a quantum computer experiment.
"""
import argparse
from fractions import Fraction
from datetime import datetime,timezone
import json
from pathlib import Path

from benchmarks.gate7_qasmbench import (
    SOURCE_BLOBS,read_source,acquire_sources,COMMIT,
)
from physqed_q.vnext import NATIVE_GATES,VNextError,compile_vnext,verify_vnext
from physqed_q.vnext_numeric import check_numeric_bound
from physqed_q.vnext_qasm import strict_import


def declared_target(n):
    return {
        "name":"PHYSQED_VNEXT_DECLARED_"+str(n)+"Q_ALL_TO_ALL",
        "qubits":n,
        "native_gates":sorted(NATIVE_GATES),
        "couplings":[[i,j] for i in range(n) for j in range(i+1,n)],
        "one_qubit_fault":"1/1000",
        "two_qubit_fault":"1/100",
        "readout_faults":["1/100"]*n,
        "provenance":"synthetic",
    }


def sweep(folder):
    report={
        "schema":"physqed-q-vnext-external-source-admission-v1",
        "created_utc":datetime.now(timezone.utc).isoformat(),
        "upstream":"pnnl/QASMBench",
        "pinned_upstream_sha":COMMIT,
        "external_source_files_declared":len(SOURCE_BLOBS),
        "source_files_unchanged":True,
        "own_frontend":True,
        "own_numeric_matrix_oracle":True,
        "qiskit_used_in_new_compiler":False,
        "pyzx_used_in_new_compiler":False,
        "fake_backend_used":False,
        "live_hardware_used":False,
        "synthetic_assumed_faults_are_real_calibration":False,
        "retrospective_expansion_of_previous_gate7_refusals":True,
        "cases":[],
    }
    for name,sha in SOURCE_BLOBS:
        text=read_source(name,folder)
        entry={"name":name,
               "source_git_blob_sha1":sha,
               "accepted":False}
        try:
            imported=strict_import(text,name="pnnl-"+name)
            program=imported["program"]
            target=declared_target(program["qubits"])
            receipt=compile_vnext(program,target,max_error="0")
            replay=verify_vnext(receipt)
            numeric=check_numeric_bound(receipt)
            # Two distinct proof stages: (1) original QASM decimal-radian
            # angles -> rational*pi using exact Machin brackets, (2)
            # rational*pi source -> target native logical program.
            # A native RZ target certifies stage 2 exactly, but does NOT
            # erase stage-1 source-angle approximation.
            qasm_bound=Fraction(imported[
                "source_to_rationalpi_projective_bound"])
            compiler_bound=Fraction(receipt["projective_operator_bound"])
            total=qasm_bound+compiler_bound
            if total>Fraction(1,1000000):
                raise VNextError(
                    "ORIGINAL_QASM_TO_NATIVE_PROJECTIVE_ERROR_BUDGET_EXCEEDED")
            entry.update({
                "accepted":True,
                "import":imported,
                "source_logical_gates":len(program["gates"]),
                "compiled_native_gates":receipt["resource_cost"]["native_gates"],
                "compiled_native_one_qubit":receipt["resource_cost"]["native_one_qubit"],
                "compiled_native_two_qubit":receipt["resource_cost"]["native_two_qubit"],
                "radian_parameter_approximation_count":len(
                    imported["decimal_radian_witnesses"]),
                "original_qasm_to_rationalpi_projective_bound":str(qasm_bound),
                "rationalpi_to_native_projective_bound":str(compiler_bound),
                "original_qasm_to_native_projective_bound":str(total),
                "exact_unmodified_source_operator_claim":bool(total==0),
                "permitted_original_qasm_projective_error":"1/1000000",
                "exact_projective_error_bound":
                    receipt["projective_operator_bound"],
                "assumed_stochastic_fault_tvd_bound":
                    receipt["stochastic_fault_tvd_bound"],
                "numerical_independent_matrix_control":numeric,
                "original_classical_measurement_mapping":
                    imported["classical_output_bit_to_quantum_qubit"],
                "deferred_measurement_order_safe_count":
                    imported["deferred_safe_disjoint_postmeasure_unitaries"],
                "receipt_sha256":receipt["receipt_sha256"],
                "receipt":receipt,
                "verification":replay,
            })
        except VNextError as exc:
            entry["refusal"]=str(exc)
        report["cases"].append(entry)
    report["accepted"]=sum(c["accepted"] for c in report["cases"])
    report["refused"]=len(report["cases"])-report["accepted"]
    if report["accepted"]<10 or len(report["cases"])!=19:
        raise RuntimeError("unanticipated external coverage regression")
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source-dir",required=True,type=Path)
    p.add_argument("--download",action="store_true")
    p.add_argument("--output",required=True,type=Path)
    args=p.parse_args()
    if args.download:
        acquire_sources(args.source_dir)
    result=sweep(args.source_dir)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print(json.dumps({
        "accepted":result["accepted"],
        "refused":result["refused"],
        "new_capability_after_gate7":[c["name"] for c in result["cases"]
             if c["accepted"] and c["name"] in {
                 "basis_change_n3","basis_trotter_n4","bell_n4",
                 "dnn_n2","inverseqft_n4","linearsolver_n3","qaoa_n3",
                 "qft_n4","quantumwalks_n2"
             }],
        "all_19_decisions":[{"name":c["name"],"accepted":c["accepted"],
                             "reason":c.get("refusal")}
                             for c in result["cases"]],
        "no_real_qpu":True,
        "no_fake_backend":True,
        "independent_matrix_checks":True,
    },sort_keys=True,indent=2))


if __name__=="__main__":
    main()
