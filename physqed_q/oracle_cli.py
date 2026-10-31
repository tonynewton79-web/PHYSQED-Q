"""Run exact adjacency-oracle experiments and replay their query receipts."""
import argparse
import json
from pathlib import Path
import sys
from .adjacency_oracle import OracleError, certify, replay, triangle_phase_program, family_triangle_phase, basis

MAX_INPUT_BYTES=262144

def unique_pairs(pairs):
    d={}
    for k,v in pairs:
        if k in d:
            raise OracleError("duplicate JSON key: "+str(k))
        d[k]=v
    return d

def load(path):
    with open(path,"rb") as stream:
        raw=stream.read(MAX_INPUT_BYTES+1)
    if len(raw)>MAX_INPUT_BYTES:
        raise OracleError("input exceeds 256 KiB")
    return json.loads(raw.decode("utf-8"),object_pairs_hook=unique_pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(OracleError("invalid JSON constant")))

def print_result(obj,output=None):
    raw=json.dumps(obj,sort_keys=True,indent=2,allow_nan=False)+"\n"
    if output:
        Path(output).write_text(raw,encoding="utf-8")
        print(json.dumps({"written":output,"receipt_sha256":obj["receipt_sha256"]},sort_keys=True))
    else:
        print(raw,end="")

def main(argv=None):
    parser=argparse.ArgumentParser(description="Exact coherent adjacency oracle and query counting")
    commands=parser.add_subparsers(dest="action",required=True)
    run=commands.add_parser("certify",help="certify JSON {program,graph,initial}")
    run.add_argument("instance")
    run.add_argument("--output")
    rep=commands.add_parser("verify",help="recompute every oracle call and exact amplitude")
    rep.add_argument("receipt")
    demo=commands.add_parser("demo",help="six-query triangle-phase example")
    demo.add_argument("--vertices",type=int,default=3)
    demo.add_argument("--output")
    fam=commands.add_parser("family",help="exhaustively verify all graphs n=3 or 4")
    fam.add_argument("--vertices",type=int,choices=(3,4),default=4)
    args=parser.parse_args(argv)
    try:
        if args.action=="verify":
            print(json.dumps(replay(load(args.receipt)),sort_keys=True,indent=2))
        elif args.action=="family":
            print(json.dumps(family_triangle_phase(args.vertices),sort_keys=True,indent=2))
        elif args.action=="demo":
            p=triangle_phase_program(args.vertices)
            g={"vertices":args.vertices,"edges":[[0,1],[0,2],[1,2]]}
            initial=basis(p,{"u":0,"v":1,"w":2})
            print_result(certify(p,g,initial),args.output)
        else:
            raw=load(args.instance)
            if not isinstance(raw,dict) or set(raw)!={"program","graph","initial"}:
                raise OracleError("instance must contain exactly program, graph, initial")
            print_result(certify(raw["program"],raw["graph"],raw["initial"]),args.output)
    except (OracleError,ValueError,TypeError,OSError,UnicodeError,IndexError,KeyError,RecursionError) as exc:
        print("REJECTED: "+str(exc),file=sys.stderr)
        return 2
    return 0

if __name__=="__main__":
    sys.exit(main())
