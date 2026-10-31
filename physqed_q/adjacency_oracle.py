"""PHYSQED-Q: bounded coherent graph-adjacency quantum oracle and query ledger.

Standard model: O_A |u,v,b> = |u,v,b XOR A_uv>.
Graph-known simulation and finite receipts are NOT an O(n)-query
algorithm for triangle finding. No hardware or Lean certificate.
"""
from __future__ import annotations

from fractions import Fraction
from itertools import combinations
import hashlib
import json
import re

from .kernel import ZERO, ONE, NEG_ONE, INV_ROOT_TWO, _apply

PROGRAM_SCHEMA = "physqed-q-adjacency-program-v1"
RECEIPT_SCHEMA = "physqed-q-adjacency-receipt-v1"
MAX_VERTICES = 8
MAX_QUBITS = 12
MAX_OPERATIONS = 128
NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,23}$")


class OracleError(ValueError):
    """Invalid graph, program, query ledger, or certificate."""


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True, allow_nan=False).encode("ascii")).hexdigest()


def integer(v):
    return type(v) is int


def graph_normalize(raw):
    if not isinstance(raw, dict) or set(raw) != {"vertices", "edges"}:
        raise OracleError("graph must contain exactly vertices and edges")
    n = raw["vertices"]
    if not integer(n) or not 2 <= n <= MAX_VERTICES or not isinstance(raw["edges"], list):
        raise OracleError("unsupported graph")
    used = set()
    for e in raw["edges"]:
        if (not isinstance(e, list) or len(e) != 2 or
            not all(integer(v) for v in e) or not (0 <= e[0] < e[1] < n) or
            tuple(e) in used):
            raise OracleError("invalid, repeated or noncanonical edge")
        used.add(tuple(e))
    return {"vertices": n, "edges": [list(e) for e in sorted(used)]}


def layout(program):
    k = (program["vertices"] - 1).bit_length()
    vs = {s: k*i for i,s in enumerate(program["vertex_registers"])}
    ans = {s: k*len(vs)+i for i,s in enumerate(program["answer_registers"])}
    return k, vs, ans, k*len(vs)+len(ans)


def program_normalize(raw):
    required = {"schema","name","vertices","vertex_registers","answer_registers","operations"}
    if not isinstance(raw, dict) or set(raw) != required:
        raise OracleError("invalid program fields")
    n = raw["vertices"]
    if raw["schema"] != PROGRAM_SCHEMA or not integer(n) or not 2 <= n <= MAX_VERTICES:
        raise OracleError("unsupported program schema or vertex count")
    name = raw["name"]
    vs = raw["vertex_registers"]
    ans = raw["answer_registers"]
    if not isinstance(name,str) or not name.strip() or len(name)>120:
        raise OracleError("invalid name")
    if not isinstance(vs,list) or not 2<=len(vs)<=3 or not isinstance(ans,list) or not 1<=len(ans)<=3:
        raise OracleError("requires 2..3 vertex and 1..3 answer registers")
    if any(not isinstance(s,str) or not NAME.fullmatch(s) for s in vs+ans) or len(set(vs+ans))!=len(vs+ans):
        raise OracleError("invalid register names")
    width = (n-1).bit_length()*len(vs)+len(ans)
    if width > MAX_QUBITS:
        raise OracleError("state exceeds 12-qubit limit")
    ops=raw["operations"]
    if not isinstance(ops,list) or len(ops)>MAX_OPERATIONS:
        raise OracleError("operations must be a bounded list")
    for op in ops:
        if not isinstance(op,dict) or not isinstance(op.get("op"),str):
            raise OracleError("invalid operation")
        kind=op["op"]
        if kind=="QUERY":
            if (set(op)!={"op","left","right","answer"} or
                op["left"] not in vs or op["right"] not in vs or
                op["left"]==op["right"] or op["answer"] not in ans):
                raise OracleError("QUERY requires distinct named vertex registers and an answer bit")
        elif kind in ("H","X","Z"):
            if set(op)!={"op","bit"} or not integer(op["bit"]) or not 0<=op["bit"]<width:
                raise OracleError("invalid single-qubit operation")
        elif kind=="CNOT":
            if (set(op)!={"op","control","target"} or
                not all(integer(op[x]) and 0<=op[x]<width for x in ("control","target")) or
                op["control"]==op["target"]):
                raise OracleError("invalid CNOT")
        elif kind=="CCZ":
            bits=op.get("bits")
            if (set(op)!={"op","bits"} or not isinstance(bits,list) or len(bits)!=3 or
                any(not integer(b) or not 0<=b<width for b in bits) or len(set(bits))!=3):
                raise OracleError("invalid CCZ")
        else:
            raise OracleError("unsupported operation (no unmetered graph read)")
    return {"schema":PROGRAM_SCHEMA,"name":name,"vertices":n,
            "vertex_registers":list(vs),"answer_registers":list(ans),
            "operations":[dict(op) for op in ops]}


def basis(program, values, answers=None):
    p=program_normalize(program)
    k,vs,ans,_=layout(p)
    if not isinstance(values,dict) or set(values)!=set(vs):
        raise OracleError("missing or extra vertex register")
    if answers is None:
        answers={a:0 for a in ans}
    if not isinstance(answers,dict) or set(answers)!=set(ans):
        raise OracleError("missing or extra answer register")
    i=0
    for s,offset in vs.items():
        v=values[s]
        if not integer(v) or not 0<=v<(1<<k):
            raise OracleError("vertex basis label invalid")
        i|=v<<offset
    for s,offset in ans.items():
        v=answers[s]
        if not integer(v) or v not in (0,1):
            raise OracleError("answer basis bit invalid")
        i|=v<<offset
    return i


def edge(graph,u,v):
    n=graph["vertices"]
    return int(u<n and v<n and u!=v and (min(u,v),max(u,v)) in graph["edge_set"])


def query_map(program,graph,op,i):
    k,vs,ans,_=layout(program)
    u=(i>>vs[op["left"]])&((1<<k)-1)
    v=(i>>vs[op["right"]])&((1<<k)-1)
    return i^(edge(graph,u,v)<<ans[op["answer"]])


def map_basis(program,graph,op,i):
    kind=op["op"]
    if kind=="QUERY":
        return query_map(program,graph,op,i),False
    if kind=="X":
        return i^(1<<op["bit"]),False
    if kind=="Z":
        return i,bool(i&(1<<op["bit"]))
    if kind=="CNOT":
        return i^((1<<op["target"]) if i&(1<<op["control"]) else 0),False
    if kind=="CCZ":
        return i,all(bool(i&(1<<b)) for b in op["bits"])
    raise OracleError("not a basis permutation")


def events(program):
    return [{"step":i,"left":op["left"],"right":op["right"],"answer":op["answer"]}
            for i,op in enumerate(program["operations"]) if op["op"]=="QUERY"]


def evolve(program,graph,initial=0):
    p=program_normalize(program)
    g=graph_normalize(graph)
    if p["vertices"]!=g["vertices"]:
        raise OracleError("graph/program mismatch")
    _,_,_,width=layout(p)
    size=1<<width
    if not integer(initial) or not 0<=initial<size:
        raise OracleError("initial basis out of range")
    gd={"vertices":g["vertices"],"edge_set":frozenset(map(tuple,g["edges"]))}
    state=[ZERO]*size
    state[initial]=ONE
    for op in p["operations"]:
        kind=op["op"]
        if kind in ("H","X","Z","CNOT"):
            qubits=([op["bit"]] if kind!="CNOT" else [op["control"],op["target"]])
            state=list(_apply(state,{"gate":kind,"qubits":qubits}))
        else:
            out=[ZERO]*size
            for i,a in enumerate(state):
                if a!=ZERO:
                    j,negative=map_basis(p,gd,op,i)
                    out[j]=(-a if negative else a)
            state=out
    return tuple(state),events(p)


def evolve_sparse(program,graph,initial=0):
    """Independent sparse scatter implementation, with exact H interference."""
    p=program_normalize(program)
    g=graph_normalize(graph)
    if p["vertices"]!=g["vertices"]:
        raise OracleError("graph/program mismatch")
    _,_,_,width=layout(p)
    if not integer(initial) or not 0<=initial<(1<<width):
        raise OracleError("invalid initial basis")
    gd={"vertices":g["vertices"],"edge_set":frozenset(map(tuple,g["edges"]))}
    state={initial:ONE}
    for op in p["operations"]:
        nxt={}
        if op["op"]=="H":
            bit=1<<op["bit"]
            for index,amp in state.items():
                h=INV_ROOT_TWO*amp
                nxt[index]=nxt.get(index,ZERO)+(-h if index&bit else h)
                j=index^bit
                nxt[j]=nxt.get(j,ZERO)+h
        else:
            for index,amp in state.items():
                j,negative=map_basis(p,gd,op,index)
                nxt[j]=nxt.get(j,ZERO)+(-amp if negative else amp)
        state={j:amp for j,amp in nxt.items() if amp!=ZERO}
    return state,events(p)


def rows(state):
    return [{"basis":i,"coefficients":list(a.coefficients())} for i,a in enumerate(state) if a!=ZERO]


def verify_oracles(program,graph):
    """Check every encoded u,v,answer pair for all used query register triples."""
    p=program_normalize(program)
    g=graph_normalize(graph)
    k,vs,ans,_=layout(p)
    gd={"vertices":g["vertices"],"edge_set":frozenset(map(tuple,g["edges"]))}
    for op in p["operations"]:
        if op["op"]!="QUERY":
            continue
        for u in range(1<<k):
            for v in range(1<<k):
                for b in (0,1):
                    i=(u<<vs[op["left"]])|(v<<vs[op["right"]])|(b<<ans[op["answer"]])
                    j=query_map(p,gd,op,i)
                    if j!=i^(edge(gd,u,v)<<ans[op["answer"]]) or query_map(p,gd,op,j)!=i:
                        raise OracleError("oracle is not its own inverse")
    return True


SCOPE={"oracle":"O_A|u,v,b>=|u,v,b XOR A_uv>",
       "query_cost":1,"free_gates":"H,X,Z,CNOT,CCZ",
       "graph_read_cost_included":False,
       "graph_independent_program_proven":False,
       "quantum_query_complexity_theorem_proven":False,
       "hardware_verified":False,"lean_kernel_verified":False,
       "verification":"exact primary gate kernel + separate sparse replay; shared oracle specification"}


def certify(program,graph,initial=0):
    p=program_normalize(program)
    g=graph_normalize(graph)
    state,ledger=evolve(p,g,initial)
    sparse,other_ledger=evolve_sparse(p,g,initial)
    if ledger!=other_ledger or sparse!={i:a for i,a in enumerate(state) if a!=ZERO}:
        raise OracleError("dense/sparse exact-evolution mismatch")
    norm=ZERO
    for a in state:
        norm=norm+a*a  # supported operations remain in the real subfield
    if norm!=ONE or not verify_oracles(p,g):
        raise OracleError("failed exact normalization/oracle involution")
    payload={"schema":RECEIPT_SCHEMA,"program":p,"graph":g,"initial":initial,
             "query_count":len(ledger),"query_ledger":ledger,
             "gate_count":len(p["operations"]),"final_state":rows(state),"scope":dict(SCOPE)}
    payload["receipt_sha256"]=digest(payload)
    replay(payload)
    return payload


def replay(receipt):
    needed={"schema","program","graph","initial","query_count","query_ledger",
            "gate_count","final_state","scope","receipt_sha256"}
    if not isinstance(receipt,dict) or set(receipt)!=needed or receipt["schema"]!=RECEIPT_SCHEMA:
        raise OracleError("unknown receipt fields/schema")
    if receipt["receipt_sha256"]!=digest({k:v for k,v in receipt.items() if k!="receipt_sha256"}):
        raise OracleError("receipt integrity hash mismatch")
    p=program_normalize(receipt["program"])
    g=graph_normalize(receipt["graph"])
    if p!=receipt["program"] or g!=receipt["graph"] or receipt["scope"]!=SCOPE:
        raise OracleError("noncanonical input or unsupported verification scope")
    state,ledger=evolve(p,g,receipt["initial"])
    sparse,sparse_ledger=evolve_sparse(p,g,receipt["initial"])
    if (receipt["query_count"]!=len(ledger) or receipt["query_ledger"]!=ledger or
        receipt["gate_count"]!=len(p["operations"]) or
        sparse_ledger!=ledger or sparse!={i:a for i,a in enumerate(state) if a!=ZERO} or
        receipt["final_state"]!=rows(state)):
        raise OracleError("incorrect query accounting or exact state")
    norm=ZERO
    for a in state:
        norm=norm+a*a
    if norm!=ONE or not verify_oracles(p,g):
        raise OracleError("exact normalization or query permutation failed")
    return {"verified":True,"query_count":len(ledger),"state_support":len(rows(state)),
            "quantum_query_complexity_theorem_proven":False}


def triangle_phase_program(n):
    if not integer(n) or not 3<=n<=MAX_VERTICES:
        raise OracleError("triangle phase requires 3..8 vertices")
    k=(n-1).bit_length()
    calls=[{"op":"QUERY","left":u,"right":v,"answer":a}
           for u,v,a in (("u","v","e_uv"),("v","w","e_vw"),("w","u","e_wu"))]
    return program_normalize({"schema":PROGRAM_SCHEMA,"name":"six-query-fixed-triple-phase",
           "vertices":n,"vertex_registers":["u","v","w"],
           "answer_registers":["e_uv","e_vw","e_wu"],
           "operations":calls+[{"op":"CCZ","bits":[3*k,3*k+1,3*k+2]}]+list(reversed(calls))})


def family_triangle_phase(n):
    """All simple labeled graphs n=3,4; fixed circuit across the graph family."""
    if not integer(n) or n not in (3,4):
        raise OracleError("exhaustive graph family limited to n=3,4")
    all_edges=list(combinations(range(n),2))
    p=triangle_phase_program(n)
    cases=0
    for m in range(1<<len(all_edges)):
        e=[list(x) for j,x in enumerate(all_edges) if m>>j&1]
        g={"vertices":n,"edges":e}
        eset=set(map(tuple,e))
        for u,v,w in combinations(range(n),3):
            initial=basis(p,{"u":u,"v":v,"w":w})
            state,ledger=evolve(p,g,initial)
            mark=int(all(x in eset for x in ((u,v),(u,w),(v,w))))
            if len(ledger)!=6 or state[initial]!=(NEG_ONE if mark else ONE) or sum(x!=ZERO for x in state)!=1:
                raise OracleError("triangle phase disagrees with independent graph truth table")
            cases+=1
    return {"verified":True,"vertices":n,"graphs":1<<len(all_edges),
            "cases":cases,"queries_per_execution":6,"triangle_finding_solved":False}
