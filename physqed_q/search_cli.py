"""Strict JSON CLI for exact ideal quantum-query triangle-search receipts."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from .adjacency_oracle import OracleError
from .triangle_search import certify_search, verify_search, exhaustive_search_family

MAX_BYTES=262144


def _unique(pairs):
    result={}
    for k,v in pairs:
        if k in result:
            raise OracleError("duplicate JSON key")
        result[k]=v
    return result


def _load(path):
    raw=Path(path).read_bytes()
    if len(raw)>MAX_BYTES:
        raise OracleError("JSON exceeds input limit")
    return json.loads(raw.decode("utf8"), object_pairs_hook=_unique,
                      parse_constant=lambda s: (_ for _ in ()).throw(OracleError("nonfinite number")))


def _print(obj,path=None):
    output=json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+"\n"
    if path is None:
        print(output,end="")
    else:
        Path(path).write_text(output,encoding="utf8")
        print(json.dumps({"file":path,"sha256":obj["receipt_sha256"]},sort_keys=True))


def main(argv=None):
    parser=argparse.ArgumentParser(description="Exact bounded coherent triangle-search query accounting")
    subs=parser.add_subparsers(dest="command",required=True)
    c=subs.add_parser("certify")
    c.add_argument("config")
    c.add_argument("--output")
    v=subs.add_parser("verify")
    v.add_argument("receipt")
    d=subs.add_parser("demo")
    d.add_argument("--vertices",type=int,default=3)
    d.add_argument("--iterations",type=int,default=1)
    d.add_argument("--verify-candidate",action="store_true")
    d.add_argument("--output")
    e=subs.add_parser("family")
    e.add_argument("--vertices",type=int,choices=(3,4),default=4)
    e.add_argument("--iterations",type=int,default=1)
    args=parser.parse_args(argv)
    try:
        if args.command=="verify":
            _print(verify_search(_load(args.receipt)))
        elif args.command=="family":
            _print(exhaustive_search_family(args.vertices,args.iterations))
        else:
            if args.command=="demo":
                cfg={"graph":{"vertices":args.vertices,"edges":[[0,1],[0,2],[1,2]]},
                     "iterations":args.iterations,
                     "verify_measured_candidate":args.verify_candidate}
            else:
                cfg=_load(args.config)
            _print(certify_search(cfg),args.output)
    except (OracleError,TypeError,ValueError,KeyError,OSError,UnicodeError,
            RecursionError,OverflowError) as exc:
        print("REJECTED: "+str(exc),file=sys.stderr)
        return 2
    return 0


if __name__=="__main__":
    sys.exit(main())
