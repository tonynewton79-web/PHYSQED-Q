"""PHYSQED-Q vNext standalone local compiler CLI.

No Qiskit, PyZX, Aer, fake backend, web access or API credentials.
A declared 'user_supplied' target is never automatically called a
verified device calibration. Only replayed mathematical statements
can be certified by this CLI.
"""
import argparse
import json
from pathlib import Path
import sys

from .vnext import VNextError, compile_vnext, verify_vnext
from .vnext_numeric import check_numeric_bound


MAX_INPUT_BYTES=131072


def pairs_unique(pairs):
    d={}
    for key,value in pairs:
        if key in d:
            raise VNextError("duplicate JSON field refused")
        d[key]=value
    return d


def read(path):
    raw=Path(path).read_bytes()
    if len(raw)>MAX_INPUT_BYTES:
        raise VNextError("input JSON exceeds bounded resource budget")
    return json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=pairs_unique,
        parse_constant=lambda x: (_ for _ in ()).throw(
            VNextError("nonfinite JSON literal refused"))
    )


def write(path,document):
    Path(path).write_text(
        json.dumps(document,sort_keys=True,indent=2,allow_nan=False)+"\n",
        encoding="utf8"
    )


def example():
    source={"name":"vnext-Rz-Rx-Ry-U3-CNOT-demo","qubits":2,
            "gates":[
                {"gate":"RZPI","qubits":[0],"angle_pi":"1/3"},
                {"gate":"RXPI","qubits":[1],"angle_pi":"-1/5"},
                {"gate":"RYPI","qubits":[0],"angle_pi":"2/7"},
                {"gate":"CNOT","qubits":[0,1]},
                {"gate":"U3PI","qubits":[1],
                 "angles_pi":["1/4","-1/3","1/6"]},
            ]}
    target={
        "name":"DECLARED_2Q_CHAIN_NO_QPU",
        "qubits":2,
        "native_gates":sorted(["H","X","Z","S","SDG","T","TDG",
                               "CNOT","CZ","SWAP"]),
        "couplings":[[0,1]],
        "one_qubit_fault":"1/1000",
        "two_qubit_fault":"1/100",
        "readout_faults":["1/100","1/100"],
        "provenance":"synthetic",
    }
    return source,target


def main(argv=None):
    p=argparse.ArgumentParser(description="PHYSQED-Q vNext analytic rotation compiler")
    sub=p.add_subparsers(dest="action",required=True)
    compilation=sub.add_parser("compile",help="compile with declared exact native/approx target")
    compilation.add_argument("source")
    compilation.add_argument("target")
    compilation.add_argument("--max-error",default="1/8",
                             help="rational upper bound on projective operator norm")
    compilation.add_argument("--output")
    compilation.add_argument("--numeric-check",action="store_true")
    verification=sub.add_parser("verify",help="replay source, target, phase and rational bounds")
    verification.add_argument("receipt")
    verification.add_argument("--numeric-check",action="store_true")
    demo=sub.add_parser("demo",help="own declared-noise target, no fake QPU")
    demo.add_argument("--mode",choices=("native","clifford_t"),default="clifford_t")
    demo.add_argument("--output")
    a=p.parse_args(argv)
    try:
        if a.action=="compile":
            result=compile_vnext(read(a.source),read(a.target),
                                 max_error=a.max_error)
        elif a.action=="verify":
            result=verify_vnext(read(a.receipt))
            if a.numeric_check:
                result["independent_numeric_spotcheck"]=check_numeric_bound(
                    read(a.receipt))
        else:
            source,target=example()
            if a.mode=="native":
                target["native_gates"].append("RZPI")
                target["native_gates"].sort()
            result=compile_vnext(source,target,max_error="1")
        if a.action in ("compile","demo"):
            if getattr(a,"numeric_check",False):
                check_numeric_bound(result)
            if a.output:
                write(a.output,result)
                print(json.dumps({
                    "written":a.output,
                    "receipt_sha256":result["receipt_sha256"],
                    "projective_operator_bound":
                        result["projective_operator_bound"],
                    "stochastic_fault_tvd_bound":
                        result["stochastic_fault_tvd_bound"],
                    "measured_QPU":False},sort_keys=True))
            else:
                print(json.dumps(result,sort_keys=True,indent=2))
        else:
            print(json.dumps(result,sort_keys=True,indent=2))
    except (VNextError,ValueError,TypeError,KeyError,IndexError,
            OSError,UnicodeError,RecursionError) as exc:
        print(f"REFUSED_VNEXT: {exc}",file=sys.stderr)
        return 2
    return 0


if __name__=="__main__":
    sys.exit(main())
