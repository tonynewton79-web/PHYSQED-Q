"""PHYSQED-Q vNext alpha: proof-carrying rational-pi rotation lowering.

STANDARD LIBRARY ONLY. Legacy v1-v3 exact receipts stay unchanged.

Native mode: exact RZPI, RXPI, RYPI, U3PI syntax lowered to RZPI +
legacy Cliffords, with explicit U3 phase.
Finite-Clifford+T mode: nearest quarter-turn phase (T^k) with global
phase accounting and an *exact rational upper bound* on the
projective operator-norm error. The bound uses pi < 22/7 and a
telescoping unitary-product inequality, not floating-point checks.

A caller-supplied, device-INDEPENDENT target supplies connectivity,
per-operation fault probabilities, and per-output readout error
probabilities. A conservative no-fault coupling gives an analytic
TVD upper bound under a declared independent stochastic-fault model.
This is not device calibration, fault-tolerance, live execution,
noise-mechanism identification, or hardware performance evidence.
"""
from fractions import Fraction
import hashlib
import json
import re

from .kernel import SINGLE, DOUBLE

SCHEMA="physqed-q-vnext-rotation-receipt-v1"
MAX_QUBITS=4
MAX_GATES=64
MAX_OUTPUT_GATES=512
MAX_JSON_BYTES=131072
ROTATIONS=frozenset(("RZPI","RXPI","RYPI","U3PI"))
NATIVE_GATES=frozenset(SINGLE | DOUBLE | {"RZPI"})
ANGLES=re.compile(r"-?(?:0|[1-9][0-9]*)(?:/[1-9][0-9]*)?\Z",re.ASCII)
PI_UPPER=Fraction(22,7)


class VNextError(ValueError):
    """Fail-closed vNext input, target, or proof violation."""


def rat(s,*,max_abs=32, max_den=1000000):
    """Only canonical bounded strings such as -3/4 or 1; never JSON float."""
    if type(s) is not str or len(s)>32 or ANGLES.fullmatch(s) is None:
        raise VNextError("rational must be canonical bounded string")
    try:
        f=Fraction(s)
    except (ValueError,ZeroDivisionError,OverflowError) as exc:
        raise VNextError("invalid exact rational") from exc
    if str(f)!=s or abs(f)>max_abs or f.denominator>max_den:
        raise VNextError("noncanonical or out-of-range exact rational")
    return f


def srat(x):
    return str(x)


def validate_program(raw):
    if type(raw) is not dict or set(raw)!={"name","qubits","gates"}:
        raise VNextError("invalid vNext program shape")
    if (type(raw["name"]) is not str or
        not 1<=len(raw["name"])<=120 or not raw["name"].strip()):
        raise VNextError("invalid program name")
    n=raw["qubits"]
    if type(n) is not int or not 1<=n<=MAX_QUBITS:
        raise VNextError("vNext bounded qubits must be integer 1..4")
    gates=raw["gates"]
    if type(gates) is not list or len(gates)>MAX_GATES:
        raise VNextError("vNext input requires at most 64 gates")
    normalized=[]
    for i,g in enumerate(gates):
        if type(g) is not dict or "gate" not in g or "qubits" not in g:
            raise VNextError(f"gate {i}: invalid shape")
        kind=g["gate"]
        if type(kind) is not str or kind not in (NATIVE_GATES | ROTATIONS):
            raise VNextError(f"gate {i}: unsupported operation")
        width=2 if kind in DOUBLE else 1
        qs=g["qubits"]
        if (type(qs) is not list or len(qs)!=width or
            any(type(q) is not int or not 0<=q<n for q in qs) or
            len(set(qs))!=width):
            raise VNextError(f"gate {i}: wrong arity/qubits")
        required=({"gate","qubits","angles_pi"} if kind=="U3PI"
                  else {"gate","qubits","angle_pi"} if kind in ROTATIONS
                  else {"gate","qubits"})
        if set(g)!=required:
            raise VNextError(f"gate {i}: extra or missing fields")
        entry={"gate":kind,"qubits":list(qs)}
        if kind=="U3PI":
            val=g["angles_pi"]
            if type(val) is not list or len(val)!=3:
                raise VNextError("U3PI needs theta, phi, lambda rational-pi")
            entry["angles_pi"]=[srat(rat(a)) for a in val]
        elif kind in ROTATIONS:
            entry["angle_pi"]=srat(rat(g["angle_pi"]))
        normalized.append(entry)
    return {"name":raw["name"],"qubits":n,"gates":normalized}


def validate_target(raw):
    required={"name","qubits","native_gates","couplings",
              "one_qubit_fault","two_qubit_fault","readout_faults",
              "provenance"}
    if type(raw) is not dict or set(raw)!=required:
        raise VNextError("target must explicitly declare all fields")
    n=raw["qubits"]
    if type(n) is not int or not 1<=n<=MAX_QUBITS:
        raise VNextError("target width outside exact bounded scope")
    name=raw["name"]
    if type(name) is not str or not 1<=len(name)<=80 or not name.strip():
        raise VNextError("invalid target name")
    provenance=raw["provenance"]
    if type(provenance) is not str or provenance not in {"synthetic","user_supplied"}:
        raise VNextError("target provenance must be explicit")
    ng=raw["native_gates"]
    if (type(ng) is not list or len(ng)>len(NATIVE_GATES) or
        len(set(ng))!=len(ng) or any(type(g) is not str or
        g not in NATIVE_GATES for g in ng)):
        raise VNextError("unknown or duplicate native gate")
    # Canonical alphabet order ensures independent replay is byte-stable.
    if ng!=sorted(ng):
        raise VNextError("native gate list must be lexically sorted")
    couplings=raw["couplings"]
    if type(couplings) is not list or len(couplings)>6:
        raise VNextError("invalid bounded coupling graph")
    edges=[]
    for pair in couplings:
        if (type(pair) is not list or len(pair)!=2 or
            any(type(q) is not int or not 0<=q<n for q in pair) or
            pair[0]>=pair[1]):
            raise VNextError("edges must be sorted distinct physical qubits")
        edges.append(list(pair))
    if edges!=sorted(edges) or len({tuple(e) for e in edges})!=len(edges):
        raise VNextError("edges not lexically sorted/unique")
    p1=rat(raw["one_qubit_fault"],max_abs=1)
    p2=rat(raw["two_qubit_fault"],max_abs=1)
    readout=raw["readout_faults"]
    if type(readout) is not list or len(readout)!=n:
        raise VNextError("readout fault probability for each physical qubit required")
    pr=[rat(x,max_abs=1) for x in readout]
    if p1<0 or p2<0 or any(p<0 for p in pr):
        raise VNextError("negative stochastic fault probability")
    return {"name":name,"qubits":n,"native_gates":list(ng),
            "couplings":edges,"one_qubit_fault":srat(p1),
            "two_qubit_fault":srat(p2),
            "readout_faults":[srat(x) for x in pr],
            "provenance":provenance}


def _nearest_quarter_turn(angle):
    """Exact half-up nearest k/4; ties deterministic even for negatives."""
    t=4*angle
    k=(t+Fraction(1,2)).numerator//(t+Fraction(1,2)).denominator
    return k


def _t_word(k,q):
    """Powers of T modulo eight; exact full-unitary phase gate P(omega)."""
    k%=8
    names={
        0:(),1:("T",),2:("S",),3:("S","T"),
        4:("Z",),5:("Z","T"),6:("SDG",),7:("TDG",),
    }[k]
    return [{"gate":kind,"qubits":[q]} for kind in names]


def _hash(document):
    raw=json.dumps(document,sort_keys=True,separators=(",",":"),
                   ensure_ascii=True,allow_nan=False).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


def _compile_semantics(source,target,tolerance):
    if source["qubits"]!=target["qubits"]:
        raise VNextError("source width and physical target do not match")
    allow=set(target["native_gates"])
    rotations_native="RZPI" in allow
    edges={tuple(x) for x in target["couplings"]}
    output=[]
    witnesses=[]
    phase=Fraction(0)
    logical_bound=Fraction(0)

    def append(kind,qs,angle=None):
        entry={"gate":kind,"qubits":list(qs)}
        if angle is not None:
            entry["angle_pi"]=str(angle)
        if kind not in allow:
            raise VNextError(f"declared target does not support lowered gate {kind}")
        if kind in DOUBLE and tuple(sorted(qs)) not in edges:
            raise VNextError("two-qubit gate not supported on physical coupling")
        output.append(entry)
        if len(output)>MAX_OUTPUT_GATES:
            raise VNextError("vNext native expansion exceeds resource budget")

    def zrotation(a,q,source_index,component):
        nonlocal phase,logical_bound
        if rotations_native:
            append("RZPI",[q],a)
            b=Fraction(0)
            implemented=a
            status="exact_native_rzpi"
        else:
            k=_nearest_quarter_turn(a)
            implemented=Fraction(k,4)
            for gate in _t_word(k,q):
                append(gate["gate"],gate["qubits"])
            phase-=Fraction(k,8)
            # ||Rz(pi*a)-Rz(pi*k/4)|| <= pi*|a-k/4|/2
            # pi < 22/7 yields exact rational upper certificate.
            b=Fraction(11,7)*abs(a-implemented)
            logical_bound+=b
            status="finite_clifford_t"
        witnesses.append({"source_index":source_index,
                          "component":component,"requested_pi":str(a),
                          "implemented_pi":str(implemented),
                          "operator_bound":str(b),"status":status})

    def emit_ry(angle,q,i):
        append("SDG",[q])
        append("H",[q])
        zrotation(angle,q,i,"theta")
        append("H",[q])
        append("S",[q])

    for i,g in enumerate(source["gates"]):
        kind=g["gate"];q=g["qubits"][0]
        if kind not in ROTATIONS:
            append(kind,g["qubits"])
        elif kind=="RZPI":
            zrotation(rat(g["angle_pi"]),q,i,"theta")
        elif kind=="RXPI":
            append("H",[q])
            zrotation(rat(g["angle_pi"]),q,i,"theta")
            append("H",[q])
        elif kind=="RYPI":
            emit_ry(rat(g["angle_pi"]),q,i)
        else:
            theta,phi,lam=[rat(x) for x in g["angles_pi"]]
            # U3(theta,phi,lambda)=exp(i*pi*(phi+lambda)/2)
            #                          * Rz(phi) * Ry(theta) * Rz(lambda).
            # Input gate order is chronological, so lambda first.
            phase+=(phi+lam)/2
            zrotation(lam,q,i,"lambda")
            emit_ry(theta,q,i)
            zrotation(phi,q,i,"phi")

    if logical_bound>tolerance:
        raise VNextError("certified projective rotation error exceeds tolerance")
    # Coupling of stochastic faults: condition on NO fault at any
    # location (including final readout). TVD can change by at most
    # probability of at least one fault. Product uses exact Q values.
    p1=rat(target["one_qubit_fault"],max_abs=1)
    p2=rat(target["two_qubit_fault"],max_abs=1)
    survival=Fraction(1)
    n1=n2=0
    for g in output:
        if len(g["qubits"])==1:
            survival*=1-p1;n1+=1
        else:
            survival*=1-p2;n2+=1
    for s in target["readout_faults"]:
        survival*=1-rat(s,max_abs=1)
    fault_bound=1-survival
    total_bound=min(Fraction(1),logical_bound+fault_bound)
    return {
        "compiled":{"name":source["name"],"qubits":source["qubits"],
                    "gates":output},
        "rotation_witnesses":witnesses,
        "global_phase_pi":str(phase),
        "projective_operator_bound":str(logical_bound),
        "stochastic_fault_tvd_bound":str(fault_bound),
        "combined_output_tvd_bound":str(total_bound),
        "resource_cost":{"source_gates":len(source["gates"]),
                         "native_gates":len(output),
                         "native_one_qubit":n1,
                         "native_two_qubit":n2},
        "rotation_mode":("exact_native" if rotations_native
                         else "bounded_clifford_t"),
    }


def _build_receipt(program,target,max_error):
    source=validate_program(program)
    hardware=validate_target(target)
    tolerance=rat(max_error,max_abs=1)
    if tolerance<0:
        raise VNextError("negative allowable projective error")
    result=_compile_semantics(source,hardware,tolerance)
    receipt={
        "schema":SCHEMA,"source":source,"target":hardware,
        "max_projective_operator_error":str(tolerance),
        **result,
        "scope":{
            "max_logical_qubits":MAX_QUBITS,
            "max_source_gates":MAX_GATES,
            "rotation_parameters":"exact rational multiples of pi",
            "error_norm":"projective operator norm global phase recorded",
            "fault_model":"declared independent stochastic local faults and readout",
            "pi_upper":"22/7",
            "exact_legacy_receipts_unchanged":True,
        },
        "claims":{
            "verified_quantum_hardware":False,
            "measured_device_calibrations":False,
            "verified_lean":False,
            "exact_rational_error_bound":True,
            "calibration_source":"declared only",
            "simulation_backends_used":False,
        },
    }
    receipt["receipt_sha256"]=_hash(receipt)
    return receipt


def compile_vnext(program,target,*,max_error="1/8"):
    document=_build_receipt(program,target,max_error)
    verify_vnext(document)
    return document


def verify_vnext(raw):
    """Independent invocation: reproduce all claims from source and target.

    Shared mathematical gate-identity templates are trusted, but no
    claimed data field, resource count, phase, angle, or bound is trusted.
    A recomputed digest is integrity-only, NOT an authenticity signature.
    """
    try:
        if type(raw) is not dict:
            raise VNextError("nonobject receipt")
        if len(json.dumps(raw,allow_nan=False,ensure_ascii=True))>MAX_JSON_BYTES:
            raise VNextError("oversize receipt")
        required={
            "schema","source","target","max_projective_operator_error",
            "compiled","rotation_witnesses","global_phase_pi",
            "projective_operator_bound","stochastic_fault_tvd_bound",
            "combined_output_tvd_bound","resource_cost","rotation_mode",
            "scope","claims","receipt_sha256",
        }
        if set(raw)!=required or raw["schema"]!=SCHEMA:
            raise VNextError("unknown or tampered receipt schema")
        digest=raw["receipt_sha256"]
        if (type(digest) is not str or len(digest)!=64 or
            any(x not in "0123456789abcdef" for x in digest)):
            raise VNextError("malformed receipt hash")
        computed=_hash({k:v for k,v in raw.items() if k!="receipt_sha256"})
        if computed!=digest:
            raise VNextError("integrity digest mismatch")
        expected=_build_receipt(
            raw["source"],raw["target"],raw["max_projective_operator_error"])
        if expected!=raw:
            raise VNextError("claimed operator, phase, resource or noise bound false")
    except (TypeError,ValueError,KeyError,IndexError,RecursionError,
            OverflowError) as exc:
        if isinstance(exc,VNextError):
            raise
        raise VNextError("malformed vNext certificate") from exc
    return {
        "verified":True,
        "scope":"bounded rational-pi gate identities and analytic error budget",
        "projective_operator_bound":raw["projective_operator_bound"],
        "stochastic_fault_tvd_bound":raw["stochastic_fault_tvd_bound"],
        "combined_output_tvd_bound":raw["combined_output_tvd_bound"],
        "hardware_verified":False,
        "actual_device_fidelity_claim":False,
    }
