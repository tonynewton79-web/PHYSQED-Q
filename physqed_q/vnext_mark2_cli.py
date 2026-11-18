"""Standalone PHYSQED-Q vNext Mark II CLI: NO fake backend or QPU."""
import argparse
import json
from pathlib import Path
import sys

from .vnext import VNextError
from .vnext_mark2 import compile_mark2,verify_mark2

MAX_INPUT=131072


def unique_pairs(pairs):
    obj={}
    for key,value in pairs:
        if key in obj:
            raise VNextError("duplicate JSON key")
        obj[key]=value
    return obj


def load(path):
    data=Path(path).read_bytes()
    if len(data)>MAX_INPUT:
        raise VNextError("Mark II input JSON exceeds size budget")
    return json.loads(
        data.decode("utf8"),object_pairs_hook=unique_pairs,
        parse_constant=lambda x: (_ for _ in ()).throw(
            VNextError("non-finite JSON literal refused")))


def example():
    src={"name":"Mark-II-own-four-qubit-line","qubits":4,
         "gates":[
             {"gate":"H","qubits":[0]},
             {"gate":"CNOT","qubits":[0,3]},
             {"gate":"RZPI","qubits":[1],"angle_pi":"1/3"},
             {"gate":"CNOT","qubits":[1,2]},
         ]}
    native=sorted(["H","X","Z","S","SDG","T","TDG","RZPI",
                   "CNOT","CZ"])  # no native SWAP: exact 3-CNOT route
    target={"name":"OWN_DECLARED_4Q_CHAIN_NO_QPU","qubits":4,
            "native_gates":native,
            "couplings":[[0,1],[1,2],[2,3]],
            "one_qubit_fault":"0","two_qubit_fault":"0",
            "readout_faults":["0","0","0","0"],
            "provenance":"synthetic"}
    envelope={
        "one_qubit_fault_upper":["1/1000","1/1100","1/1200","1/1300"],
        "two_qubit_fault_upper_by_edge":[
            [0,1,"1/200"],[1,2,"1/175"],[2,3,"1/150"]],
        "readout_fault_upper":["1/50","1/60","1/70","1/80"],
        "fault_semantics":"marginal_fault_event_upper_bounds",
        "provenance":"synthetic"}
    return src,target,envelope


def main(argv=None):
    p=argparse.ArgumentParser(
        description="PHYSQED-Q Mark II deterministic, model-only physical router")
    sub=p.add_subparsers(dest="command",required=True)
    build=sub.add_parser("route",help="route source and produce proof-carrying receipt")
    build.add_argument("program")
    build.add_argument("target")
    build.add_argument("error_envelope")
    build.add_argument("--max-error",default="1/8")
    build.add_argument("--initial-layout",default=None,
                       help="JSON array of logical->physical initial wire assignment")
    build.add_argument("--classical-map",default=None,
                       help="JSON array of classical bit->logical qubit")
    build.add_argument("--physical-outputs",default=None,
                       help="JSON array of classical bit->required physical measurement")
    build.add_argument("--output")
    verification=sub.add_parser("verify",help="independent replay of entire routed receipt")
    verification.add_argument("receipt")
    demo=sub.add_parser("demo",help="run fully native declared 4-wire chain example")
    demo.add_argument("--output")
    a=p.parse_args(argv)
    try:
        if a.command=="verify":
            result=verify_mark2(load(a.receipt))
        else:
            if a.command=="demo":
                src,tgt,env=example()
                result=compile_mark2(
                    src,tgt,env,
                    required_physical_qubits_for_classical_bits=[3,2,1,0],
                    max_projective_error="0")
            else:
                def array(field):
                    value=getattr(a,field)
                    return None if value is None else json.loads(value)
                result=compile_mark2(
                    load(a.program),load(a.target),load(a.error_envelope),
                    initial_logical_to_physical=array("initial_layout"),
                    classical_output_bit_to_logical_qubit=array("classical_map"),
                    required_physical_qubits_for_classical_bits=array(
                        "physical_outputs"),
                    max_projective_error=a.max_error)
        if getattr(a,"output",None):
            Path(a.output).write_text(
                json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n",
                encoding="utf8")
            print(json.dumps({
                "written":a.output,
                "receipt_sha256":result["receipt_sha256"],
                "native_two_qubit_gates":result["cost"]["physical_native_two_qubit"],
                "inserted_swaps":result["cost"]["inserted_local_swaps"],
                "physical_measurement_mapping":[
                    v["physical_qubit"]
                    for v in result["physical_output_measurements"]],
                "simulated_not_hardware":True},sort_keys=True))
        else:
            print(json.dumps(result,sort_keys=True,indent=2,allow_nan=False))
    except (VNextError,ValueError,TypeError,KeyError,IndexError,
            UnicodeError,OSError,RecursionError) as exc:
        print("REFUSED_MARK2: "+str(exc),file=sys.stderr)
        return 2
    return 0


if __name__=="__main__":
    sys.exit(main())
