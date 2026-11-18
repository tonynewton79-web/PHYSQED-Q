"""PHYSQED-Q vNext Mark II: verified, device-independent physical routing.

STANDARD LIBRARY ONLY: no Qiskit, Aer, PyZX, fake backend or QPU.
The Alpha compiler first lowers a rational-pi program on a declared
VIRTUAL complete logical graph (NOT hardware); this Mark II layer
routes all native gates onto the declared physical undirected graph.

The deterministic BFS minimizes SWAP count for each *local* interaction
and the final measured-output constraint. This is NOT globally optimal
routing, depth, fidelity or 2Q gate count. All additional physical SWAPs
are retained as SWAP or expanded to 3 bidirectional CNOTs.

The exact rational noise envelope uses marginal per-site/edge/readout
fault-event probability upper bounds, NOT measured calibrations. The
union fault bound is conservative even under correlation, conditional
on a no-fault execution producing the specified logical circuit.
"""
from collections import deque
from fractions import Fraction

from .vnext import (VNextError, compile_vnext, validate_program,
                    validate_target, verify_vnext, rat, _hash)

SCHEMA = "physqed-q-vnext-mark2-routed-receipt-v1"
MAX_PHYSICAL_GATES = 4096
MAX_ROUTING_SWAPS = 1024
MAX_RECEIPT_CHARS = 3000000


def permutation(data, n, description):
    if (type(data) is not list or len(data) != n or
        any(type(x) is not int for x in data) or
        sorted(data) != list(range(n))):
        raise VNextError(description + " requires a complete bijection")
    return tuple(data)


def fault(value):
    result = rat(value,max_abs=1)
    if result < 0:
        raise VNextError("negative declared fault upper")
    return result


def validate_error_envelope(raw,target):
    keys={"one_qubit_fault_upper","two_qubit_fault_upper_by_edge",
          "readout_fault_upper","provenance","fault_semantics"}
    if type(raw) is not dict or set(raw)!=keys:
        raise VNextError("missing heterogeneous physical error envelope")
    n=target["qubits"]
    one,readout,edges=(raw["one_qubit_fault_upper"],
                       raw["readout_fault_upper"],
                       raw["two_qubit_fault_upper_by_edge"])
    if (type(one) is not list or len(one)!=n or
        type(readout) is not list or len(readout)!=n or
        type(edges) is not list or len(edges)!=len(target["couplings"])):
        raise VNextError("missing physical or edge fault entry")
    one=[str(fault(x)) for x in one]
    readout=[str(fault(x)) for x in readout]
    bounded=[]
    for expected,record in zip(target["couplings"],edges):
        if (type(record) is not list or len(record)!=3 or
            type(record[0]) is not int or type(record[1]) is not int or
            record[:2]!=expected):
            raise VNextError("physical edge faults must match sorted coupling list")
        bounded.append([expected[0],expected[1],str(fault(record[2]))])
    if (type(raw["provenance"]) is not str or
        raw["provenance"] not in ("synthetic","user_supplied_unverified") or
        raw["fault_semantics"]!="marginal_fault_event_upper_bounds"):
        raise VNextError("unsupported provenance or error semantics")
    return {"one_qubit_fault_upper":one,
            "two_qubit_fault_upper_by_edge":bounded,
            "readout_fault_upper":readout,
            "provenance":raw["provenance"],
            "fault_semantics":"marginal_fault_event_upper_bounds"}


def shortest_swaps(start,edges,goal):
    """Deterministic breadth-first search over wire-token permutations."""
    start=tuple(start)
    edges=tuple(tuple(e) for e in edges)
    if goal(start):
        return []
    queue=deque([start])
    seen={start:(None,None)}
    while queue:
        current=queue.popleft()
        for a,b in edges:
            nxt=tuple(b if q==a else a if q==b else q for q in current)
            if nxt in seen:
                continue
            seen[nxt]=(current,(a,b))
            if goal(nxt):
                answer=[]
                pos=nxt
                while seen[pos][0] is not None:
                    prev,edge=seen[pos]
                    answer.append(list(edge))
                    pos=prev
                return list(reversed(answer))
            queue.append(nxt)
    raise VNextError("NO_PHYSICALLY_CONNECTED_ROUTING_PATH")


def derive(source,target,envelope,initial,classtological,output,max_error):
    n=target["qubits"]
    # The all-to-all logical synthesis is NEVER represented as hardware.
    virtual=dict(target)
    virtual.update({
        "name":"VIRTUAL_ALL_TO_ALL_LOWERING_NOT_HARDWARE",
        "couplings":[[a,b] for a in range(n) for b in range(a+1,n)],
        "one_qubit_fault":"0","two_qubit_fault":"0",
        "readout_faults":["0"]*n,"provenance":"synthetic",
    })
    logical=compile_vnext(source,virtual,max_error=max_error)
    edges=tuple(tuple(e) for e in target["couplings"])
    edge_set=set(edges)
    allowed=set(target["native_gates"])
    if not edges and any(len(g["qubits"])==2
                         for g in logical["compiled"]["gates"]):
        raise VNextError("NO_NATIVE_TWO_QUBIT_COUPLINGS")
    positions=list(initial)
    initial_wire_tokens=list(range(n))
    native=[]
    swaps=[]
    local_routes=[]

    def emit(kind,qubits,angle=None):
        if kind not in allowed:
            raise VNextError("NATIVE_TARGET_GATE_UNSUPPORTED: "+kind)
        if len(qubits)==2 and tuple(sorted(qubits)) not in edge_set:
            raise VNextError("NONLOCAL_NATIVE_TWO_QUBIT_OPERATION")
        operation={"gate":kind,"qubits":list(qubits)}
        if angle is not None:
            operation["angle_pi"]=angle
        native.append(operation)
        if len(native)>MAX_PHYSICAL_GATES:
            raise VNextError("MARK2_NATIVE_GATE_BUDGET_EXCEEDED")

    def move(a,b,source_index):
        if tuple(sorted((a,b))) not in edge_set:
            raise VNextError("NONLOCAL_ROUTING_SWAP")
        if "SWAP" in allowed:
            emit("SWAP",[a,b])
            cost=1
        elif "CNOT" in allowed:
            # Undirected declared coupling explicitly assumes both CX
            # orientations are physically available in this target model.
            emit("CNOT",[a,b])
            emit("CNOT",[b,a])
            emit("CNOT",[a,b])
            cost=3
        else:
            raise VNextError("NATIVE_SWAP_OR_BIDIRECTIONAL_CNOT_REQUIRED")
        positions[:]=[b if q==a else a if q==b else q for q in positions]
        initial_wire_tokens[:]=[
            b if q==a else a if q==b else q for q in initial_wire_tokens
        ]
        swaps.append({
            "after_source_gate":source_index,
            "physical_edge":[a,b],
            "decomposed_two_qubit_gate_count":cost,
            "resulting_logical_to_physical":list(positions),
        })
        if len(swaps)>MAX_ROUTING_SWAPS:
            raise VNextError("MARK2_ROUTING_SWAP_BUDGET_EXCEEDED")

    for index,g in enumerate(logical["compiled"]["gates"]):
        q=g["qubits"]
        if len(q)==2:
            a,b=q
            if tuple(sorted((positions[a],positions[b]))) not in edge_set:
                previous=list(positions)
                path=shortest_swaps(
                    positions,edges,
                    lambda state,a=a,b=b:
                        tuple(sorted((state[a],state[b]))) in edge_set
                )
                for x,y in path:
                    move(x,y,index)
                local_routes.append({
                    "source_native_gate_index":index,
                    "initial_logical_to_physical":previous,
                    "swap_path":path,
                    "final_logical_to_physical":list(positions),
                })
        emit(g["gate"],[positions[j] for j in q],g.get("angle_pi"))

    desired=[0]*n
    for classical_bit,logical_wire in enumerate(classtological):
        desired[logical_wire]=output[classical_bit]
    final_path=shortest_swaps(
        positions,edges,lambda state:state==tuple(desired)
    )
    for a,b in final_path:
        move(a,b,len(logical["compiled"]["gates"]))
    if positions!=desired:
        raise VNextError("FINAL_MEASUREMENT_ROUTING_INCOMPLETE")
    readouts=[{"classical_bit":c,"logical_qubit":logical_wire,
               "physical_qubit":positions[logical_wire]}
              for c,logical_wire in enumerate(classtological)]
    if [m["physical_qubit"] for m in readouts]!=list(output):
        raise VNextError("PHYSICAL_OUTPUT_MAP_NOT_ENFORCED")

    p1=[Fraction(x) for x in envelope["one_qubit_fault_upper"]]
    p2={tuple(e[:2]):Fraction(e[2])
        for e in envelope["two_qubit_fault_upper_by_edge"]}
    pr=[Fraction(x) for x in envelope["readout_fault_upper"]]
    fault_sum=Fraction(0)
    one=two=0
    depth=[0]*n
    for op in native:
        q=op["qubits"]
        if len(q)==1:
            one+=1
            fault_sum+=p1[q[0]]
        else:
            two+=1
            fault_sum+=p2[tuple(sorted(q))]
        finish=max(depth[j] for j in q)+1
        for j in q:
            depth[j]=finish
    for readout in readouts:
        fault_sum+=pr[readout["physical_qubit"]]
    fault_upper=min(Fraction(1),fault_sum)
    logical_upper=Fraction(logical["projective_operator_bound"])
    return {
        "virtual_lowering_receipt":logical,
        "native_circuit":{"name":source["name"],"qubits":n,"gates":native},
        "physical_output_measurements":readouts,
        "physical_initial_logical_layout":list(initial),
        "physical_final_logical_layout":list(positions),
        "end_permutation_of_input_wire_states":initial_wire_tokens,
        "routing_swap_ledger":swaps,
        "per_gate_shortest_local_routes":local_routes,
        "final_output_swap_path":final_path,
        "cost":{
            "logical_lowered_gates":len(logical["compiled"]["gates"]),
            "physical_native_gates":len(native),
            "physical_native_one_qubit":one,
            "physical_native_two_qubit":two,
            "inserted_local_swaps":len(swaps),
            "native_depth_unit_weight":max(depth,default=0),
        },
        "logical_projective_operator_bound":str(logical_upper),
        "correlation_robust_marginal_fault_union_bound":str(fault_upper),
        "combined_output_tvd_upper_bound":
            str(min(Fraction(1),logical_upper+fault_upper)),
        "claim_scope":{
            "physical_native_circuit_is_executable_on_declared_undirected_couplings":True,
            "local_bfs_minimum_swap_count_only":True,
            "whole_circuit_optimality_proved":False,
            "hardware_execution_performed":False,
            "independently_verified_calibration":False,
            "extra_unused_physical_qubits_supported":False,
            "physical_target_is_user_declaration_not_verified_device":True,
            "all_noise_claims_conditional_on_declared_marginal_fault_events":True,
            "no_fake_backend":True,
        },
    }


def _build(source,physical_target,error_envelope,initial_layout,
           classical_map,physical_output,max_error):
    src=validate_program(source)
    target=validate_target(physical_target)
    n=target["qubits"]
    if n!=src["qubits"]:
        raise VNextError("MARK2_REQUIRES_PHYSICAL_WIDTH_EQUALS_LOGICAL_WIDTH")
    if (target["one_qubit_fault"]!="0" or
        target["two_qubit_fault"]!="0" or
        any(v!="0" for v in target["readout_faults"])):
        raise VNextError("USE_MARK2_HETEROGENEOUS_ENVELOPE_NOT_ALPHA_FAULT_FIELDS")
    envelope=validate_error_envelope(error_envelope,target)
    start=permutation(initial_layout,n,"initial layout")
    classical=permutation(classical_map,n,"classical mapping")
    final=permutation(physical_output,n,"measured output mapping")
    tol=rat(max_error,max_abs=1)
    if tol<0:
        raise VNextError("negative Mark II projective budget")
    body=derive(src,target,envelope,start,classical,final,max_error)
    result={
        "schema":SCHEMA,
        "source":src,
        "physical_target":target,
        "physical_fault_envelope":envelope,
        "initial_logical_to_physical":list(start),
        "classical_output_bit_to_logical_qubit":list(classical),
        "required_physical_qubits_for_classical_bits":list(final),
        "requested_max_projective_error":str(tol),
        **body,
    }
    result["receipt_sha256"]=_hash(result)
    return result


def compile_mark2(source,physical_target,error_envelope,*,
                  initial_logical_to_physical=None,
                  classical_output_bit_to_logical_qubit=None,
                  required_physical_qubits_for_classical_bits=None,
                  max_projective_error="1/8"):
    n=source.get("qubits") if type(source) is dict else None
    if type(n) is not int or not 1<=n<=4:
        raise VNextError("invalid bounded Mark II source width")
    initial=(list(range(n)) if initial_logical_to_physical is None
             else initial_logical_to_physical)
    classical=(list(range(n)) if classical_output_bit_to_logical_qubit is None
               else classical_output_bit_to_logical_qubit)
    outputs=(list(range(n)) if required_physical_qubits_for_classical_bits is None
             else required_physical_qubits_for_classical_bits)
    receipt=_build(source,physical_target,error_envelope,initial,
                   classical,outputs,max_projective_error)
    verify_mark2(receipt)
    return receipt


def verify_mark2(receipt):
    """Recompute complete source-to-target routing and all rational costs."""
    if type(receipt) is not dict:
        raise VNextError("invalid Mark II receipt object")
    try:
        if len(str(receipt))>MAX_RECEIPT_CHARS:
            raise VNextError("Mark II receipt exceeds proof resource bound")
        if receipt.get("schema")!=SCHEMA:
            raise VNextError("unknown Mark II receipt schema")
        if type(receipt.get("receipt_sha256")) is not str:
            raise VNextError("malformed receipt digest")
        digest=_hash({k:v for k,v in receipt.items() if k!="receipt_sha256"})
        if digest!=receipt["receipt_sha256"]:
            raise VNextError("Mark II receipt integrity mismatch")
        expected=_build(
            receipt["source"],receipt["physical_target"],
            receipt["physical_fault_envelope"],
            receipt["initial_logical_to_physical"],
            receipt["classical_output_bit_to_logical_qubit"],
            receipt["required_physical_qubits_for_classical_bits"],
            receipt["requested_max_projective_error"],
        )
        if expected!=receipt:
            raise VNextError("Mark II false routing, gates, costs or fault certificate")
        verify_vnext(receipt["virtual_lowering_receipt"])
    except (ValueError,TypeError,KeyError,IndexError,RecursionError,
            OverflowError) as exc:
        if isinstance(exc,VNextError):
            raise
        raise VNextError("malformed Mark II certificate") from exc
    return {
        "verified":True,
        "native_operations_checked":len(receipt["native_circuit"]["gates"]),
        "routing_swaps_verified":len(receipt["routing_swap_ledger"]),
        "combined_output_tvd_upper_bound":receipt["combined_output_tvd_upper_bound"],
        "hardware_verified":False,
        "independently_measured_calibration":False,
    }
