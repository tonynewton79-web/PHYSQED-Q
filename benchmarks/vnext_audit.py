"""Independent source-data and rational angle-certification replay for vNext.

Reopens ALL 19 original SHA-pinned published QASMBench sources,
reconstructs every admission/refusal, verifies every compile receipt,
and independently verifies Machin-based source-angle error witnesses
using literal rational endpoint arithmetic. Dense matrix oracle
remains a separate independent numerical implementation.

This independently audits the data/result ledger; it shares the
front-end and compiler mathematical rewrite rules with the system,
so it is not an independent formal prover or physics experiment.
"""
import argparse
from fractions import Fraction
import json
from pathlib import Path

from benchmarks.gate7_qasmbench import SOURCE_BLOBS,read_source,COMMIT
from benchmarks.vnext_external_qasmbench import declared_target
from physqed_q.vnext import (
    VNextError,compile_vnext,verify_vnext
)
from physqed_q.vnext_numeric import check_numeric_bound
from physqed_q.vnext_qasm import strict_import
from physqed_q.pi_interval import PI_LOWER,PI_UPPER


def audit(report, folder):
    if (report.get("schema")!="physqed-q-vnext-external-source-admission-v1"
        or report.get("pinned_upstream_sha")!=COMMIT
        or not report.get("own_frontend")
        or report.get("fake_backend_used")
        or report.get("live_hardware_used")
        or report.get("synthetic_assumed_faults_are_real_calibration")):
        raise RuntimeError("incorrect vNext provenance")
    cases=report.get("cases")
    if type(cases) is not list or len(cases)!=19:
        raise RuntimeError("omitted published benchmark")
    if [c["name"] for c in cases]!=[n for n,_ in SOURCE_BLOBS]:
        raise RuntimeError("changed ordering of frozen external sources")
    accepted=0
    converted_angles=0
    receipts=0
    for (name,source_sha),entry in zip(SOURCE_BLOBS,cases):
        text=read_source(name,folder)
        if entry["source_git_blob_sha1"]!=source_sha:
            raise RuntimeError("false external source identity")
        expected_error=None
        try:
            parsed=strict_import(text,name="pnnl-"+name)
            source=parsed["program"]
            receipt=compile_vnext(source,declared_target(source["qubits"]),
                                   max_error="0")
            verify_vnext(receipt)
            check_numeric_bound(receipt)
        except VNextError as exc:
            expected_error=str(exc)
        if expected_error is not None:
            if entry.get("accepted") or entry.get("refusal")!=expected_error:
                raise RuntimeError("wrong unmodified QASMBench admission refusal")
            continue
        if not entry.get("accepted"):
            raise RuntimeError("accepted original was silently suppressed")
        if parsed!=entry["import"] or receipt!=entry["receipt"]:
            raise RuntimeError("forged imported source or receipt")
        upper=Fraction(0)
        for witness in parsed["decimal_radian_witnesses"]:
            theta=Fraction(witness["original_decimal_radians"])
            a=Fraction(witness["replacement_rational_pi"])
            derived=max(abs(theta-PI_LOWER*a),abs(theta-PI_UPPER*a))
            if derived!=Fraction(witness["absolute_angle_error_upper"]):
                raise RuntimeError("incorrect Machin decimal-radian bound")
            if derived/2!=Fraction(witness["projective_operator_bound"]):
                raise RuntimeError("invalid rotational projective norm")
            upper+=derived/2
            converted_angles+=1
        if upper!=Fraction(parsed["source_to_rationalpi_projective_bound"]):
            raise RuntimeError("omitted original angle approximation")
        actual=upper+Fraction(receipt["projective_operator_bound"])
        if actual>Fraction(1,1000000):
            raise RuntimeError("external source error target exceeded")
        if actual!=Fraction(entry["original_qasm_to_native_projective_bound"]):
            raise RuntimeError("false original source-to-native error")
        if (entry["radian_parameter_approximation_count"]!=
            len(parsed["decimal_radian_witnesses"])):
            raise RuntimeError("wrong angle-approximation count")
        if entry["source_logical_gates"]!=len(source["gates"]):
            raise RuntimeError("incorrect logical gate count")
        if entry["compiled_native_gates"]!=len(receipt["compiled"]["gates"]):
            raise RuntimeError("incorrect native gate count")
        if entry["receipt_sha256"]!=receipt["receipt_sha256"]:
            raise RuntimeError("inconsistent independent receipt replay")
        accepted+=1
        receipts+=1
    if report["accepted"]!=accepted or report["refused"]!=19-accepted:
        raise RuntimeError("admission ledger count mismatch")
    if accepted!=15:
        raise RuntimeError("locked research-source corpus changed coverage")
    return {
        "schema":"physqed-q-vnext-external-numeric-rational-audit-v1",
        "status":"PASS",
        "upstream_source_sha":COMMIT,
        "original_sources_fully_checked":19,
        "accepted_and_receipt_replayed":receipts,
        "refused_with_explicit_reason":19-accepted,
        "decimal_radian_rotation_witnesses_audited":converted_angles,
        "verified_hardware":False,
        "uses_fake_IBM_backends":False,
        "independent_formal_prover":False,
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("input",type=Path)
    p.add_argument("--source-dir",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    result=audit(json.loads(args.input.read_text()),args.source_dir)
    args.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print(json.dumps(result,sort_keys=True))


if __name__=="__main__":
    main()
