"""OPTIONAL independent physical-unitary cross-check, not a compiler dependency.

Qiskit interprets the *original, hash-pinned published QASMBench QASM*
as an independent reference. Remove final and safe-to-defer measurements
only after the own strict parser has certified no measured qubit is
acted on afterwards. Compare that Qiskit unitary to the independently
implemented dense-complex PHYSQED-Q vNext input operator, up to global
phase, within the exact rational Machin error budget.

This is independent solver validation; it is not live quantum hardware
and does not assert the approximated decimal-radian input is exactly
unitary equal to the source.
"""
import argparse
from fractions import Fraction
import json
import math
from pathlib import Path

from benchmarks.gate7_qasmbench import SOURCE_BLOBS,read_source
from physqed_q.vnext_qasm import strict_import
from physqed_q.vnext_numeric import numeric_unitary
from physqed_q.vnext import VNextError


def dense_qiskit_original(text):
    from qiskit import QuantumCircuit, qasm2
    from qiskit.quantum_info import Operator
    parsed=qasm2.loads(text,strict=True)
    circuit=QuantumCircuit(parsed.num_qubits)
    for item in parsed.data:
        if item.operation.name in ("measure","barrier"):
            continue
        if item.clbits or item.operation.num_clbits:
            raise VNextError("independent reference has active classical control")
        physical=[parsed.find_bit(q).index for q in item.qubits]
        circuit.append(item.operation,physical)
    return Operator(circuit).data


def projective_frobenius(reference,ours):
    n=len(ours)
    # The complex trace overlap gives the unique Frobenius-optimal
    # relative global phase, if nonzero. It is NOT an independent proof.
    overlap=0j
    for c in range(n):
        for r in range(n):
            overlap+=reference[r,c]*ours[c][r].conjugate()
    if abs(overlap)<1e-9:
        raise RuntimeError("unitaries nearly orthogonal; no stable phase check")
    phase=overlap/abs(overlap)
    delta=0.
    for c in range(n):
        for r in range(n):
            delta+=abs(reference[r,c]-phase*ours[c][r])**2
    return math.sqrt(delta),phase


def audit(folder):
    cases=[]
    for name,_ in SOURCE_BLOBS:
        src=read_source(name,folder)
        try:
            imp=strict_import(src,name="pnnl-"+name)
        except VNextError as exc:
            cases.append({"name":name,"admitted":False,"reason":str(exc)})
            continue
        reference=dense_qiskit_original(src)
        ours=numeric_unitary(imp["program"])
        d,phase=projective_frobenius(reference,ours)
        d_hilbert=1<<imp["program"]["qubits"]
        budget=Fraction(imp["source_to_rationalpi_projective_bound"])
        max_fro=math.sqrt(d_hilbert)*float(budget)+2e-8
        if d>max_fro:
            raise RuntimeError(
                f"independent Qiskit original QASM discrepancy {name}: "
                f"actual Frobenius {d} exceeds certified target {max_fro}")
        cases.append({
            "name":name,"admitted":True,
            "qubits":imp["program"]["qubits"],
            "original_qasm_independent_frobenius_projective":d,
            "proven_frobenius_upper_from_rational_projective_bound":
                max_fro,
            "exact_rational_projective_bound":str(budget),
            "original_decimal_radian_rotation_count":
                len(imp["decimal_radian_witnesses"]),
            "measurement_bit_to_qubit":
                imp["classical_output_bit_to_quantum_qubit"],
        })
    passed=sum(c["admitted"] for c in cases)
    if passed!=15:
        raise RuntimeError("unexpected admitted external PNNL source count")
    return {
        "schema":"physqed-q-vnext-independent-qiskit-original-operator-v1",
        "status":"PASS",
        "number_published_external_sources":len(cases),
        "admitted_originals_with_independent_full_operator_check":passed,
        "qiskit_compiler_used_in_vnext":False,
        "fake_backends_used":False,
        "hardware_measurement_performed":False,
        "tests_numerical_not_formal":True,
        "cases":cases,
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source-dir",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    result=audit(args.source_dir)
    args.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print(json.dumps({
        "status":result["status"],
        "source_circuits":result["number_published_external_sources"],
        "independent_operators_checked":
            result["admitted_originals_with_independent_full_operator_check"],
        "max_projective_frobenius_observed":max(
            c["original_qasm_independent_frobenius_projective"]
            for c in result["cases"] if c["admitted"]),
        "real_hardware":False,
    },sort_keys=True))


if __name__=="__main__":
    main()
