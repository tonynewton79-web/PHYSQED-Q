"""Fail-closed OpenQASM 2 subset importer for PHYSQED-Q vNext.

This is a small *owned* front-end; no Qiskit, Aer, PyZX or fake backend.
The original external QASM source remains unchanged and SHA tracked.

Supported bounded declarations: OPENQASM 2.0; qelib1.inc; named
single registers qreg/creg; H X Z S SDG T TDG CX CZ SWAP; rotations
rz rx ry and u3 with exact rational multiples of pi. Bare finite
decimal radians are converted to bounded rational-pi angles ONLY with
an explicit rational error certificate derived from Machin pi bounds.
Measurements are tracked using original classical register order,
including nonidentity output mapping. A measurement can be moved
to the end only if no subsequent unitary touches that measured qubit
and no classical conditions, reset, or feedback occur. This restricted
deferral preserves the joint computational-basis output distribution.
No claim is made for general midcircuit/dynamic circuits.
"""
from fractions import Fraction
import hashlib
import re

from .vnext import VNextError,validate_program,rat
from .kernel import SINGLE,DOUBLE
from .pi_interval import approximate_decimal_radians_as_pi,PI_LOWER,PI_UPPER

MAX_BYTES=40000
_IDENT=r"[A-Za-z_][A-Za-z_0-9]*"
REF=re.compile(rf"^({_IDENT})\[(\d+)\]$",re.ASCII)
DECL=re.compile(rf"^(qreg|creg)\s+({_IDENT})\[(\d+)\]$",re.ASCII)
OP=re.compile(r"^([a-z][a-z0-9]*)\s+(.+)$",re.ASCII)
PARAM_OP=re.compile(r"^([a-z][a-z0-9]*)\s*\(([^()]*)\)\s+(.+)$",re.ASCII)
PI_FLOAT=re.compile(
    r"^([+-]?)pi(?:\s*\*\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?))?$",
    re.ASCII
)
PLAIN_NUMERIC=re.compile(
    r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$",
    re.ASCII
)
MAP=dict(zip(
    ("h","x","z","s","sdg","t","tdg","cx","cz","swap",
     "rz","rx","ry","u3"),
    ("H","X","Z","S","SDG","T","TDG","CNOT","CZ","SWAP",
     "RZPI","RXPI","RYPI","U3PI")
))


def _angle_with_certificate(token):
    """(rational-pi coefficient, rigorous absolute radian error upper)."""
    text=token.strip().replace(" ","")
    if text in ("0","+0","-0","0.0","+0.0","-0.0"):
        return "0",Fraction(0)
    match=PI_FLOAT.fullmatch(text)
    if match is not None:
        leading= -1 if match.group(1)=="-" else 1
        number=match.group(2)
        if number is None:
            fraction=Fraction(leading)
        else:
            fraction=Fraction(number)*leading
        if abs(fraction)>32 or fraction.denominator>1000000000000:
            raise VNextError("ANGLE_RATIONAL_BOUND_EXCEEDED")
        out=str(fraction)
        rat(out)
        return out,Fraction(0)
    if PLAIN_NUMERIC.fullmatch(text):
        try:
            theta=Fraction(text)
            approx,delta=approximate_decimal_radians_as_pi(theta)
            out=str(approx)
            rat(out)
            return out,delta
        except (ValueError,OverflowError,ZeroDivisionError) as exc:
            raise VNextError("DECIMAL_RADIAN_CERTIFICATION_REFUSED") from exc
    raise VNextError("UNSUPPORTED_ANGLE_EXPRESSION: "+text[:45])


def fractional_pi(token):
    """Compat helper: returns coefficient only; strict importer records error."""
    return _angle_with_certificate(token)[0]


def strict_import(text,*,name="external-qasm"):
    if type(text) is not str or len(text.encode("utf8"))>MAX_BYTES:
        raise VNextError("QASM source exceeds bounded input")
    cleaned="\n".join(line.split("//",1)[0] for line in text.splitlines())
    statements=[x.strip() for x in cleaned.split(";") if x.strip()]
    if not statements or statements[0].replace(" ","")!="OPENQASM2.0":
        raise VNextError("QASM_VERSION_2_REQUIRED")
    if len(statements)<2 or statements[1] not in (
        'include "qelib1.inc"', "include 'qelib1.inc'"):
        raise VNextError("QELIB1_DECLARATION_REQUIRED")
    qregs={};cregs={};nq=0;nc=0
    gates=[];measures={};started_operations=False
    deferred_count=0
    radian_witnesses=[]
    import_projective_bound=Fraction(0)
    for index,statement in enumerate(statements[2:],2):
        stmt=statement.strip()
        declaration=DECL.fullmatch(stmt)
        if declaration:
            if started_operations:
                raise VNextError("LATE_REGISTER_DECLARATION")
            kind,key,size=declaration.groups()
            width=int(size)
            if not 1<=width<=4:
                raise VNextError("INVALID_BOUNDED_REGISTER_SIZE")
            if key in qregs or key in cregs:
                raise VNextError("DUPLICATE_REGISTER")
            if kind=="qreg":
                qregs[key]=(nq,width)
                nq+=width
            else:
                cregs[key]=(nc,width)
                nc+=width
            if nq>4 or nc>4:
                raise VNextError("QASM_WIDTH_OUT_OF_SCOPE")
            continue
        started_operations=True
        if stmt.lower().startswith("barrier "):
            # Barriers are compiler-order directives, not unitary.
            # We do NOT permit a barrier to hide classical feedback.
            continue
        if stmt.lower().startswith("measure "):
            expression=stmt[8:].strip()
            parts=expression.split("->")
            if len(parts)!=2:
                raise VNextError("INVALID_MEASUREMENT")
            qpart=REF.fullmatch(parts[0].strip())
            cpart=REF.fullmatch(parts[1].strip())
            if qpart is None or cpart is None:
                raise VNextError("QASM_MEASURE_ALL_REGISTER_UNSUPPORTED")
            qname,qindex=qpart.groups()
            cname,cindex=cpart.groups()
            if qname not in qregs or cname not in cregs:
                raise VNextError("UNDECLARED_MEASUREMENT_REGISTER")
            qo,qw=qregs[qname];co,cw=cregs[cname]
            qi=int(qindex);ci=int(cindex)
            if qi>=qw or ci>=cw:
                raise VNextError("MEASUREMENT_INDEX_OUT_OF_RANGE")
            qubit=qo+qi
            cbit=co+ci
            if cbit in measures or qubit in measures.values():
                raise VNextError("DUPLICATE_OR_CONFLICTING_MEASUREMENT")
            measures[cbit]=qubit
            continue
        if stmt.startswith("if") or stmt.startswith("reset"):
            raise VNextError("DYNAMIC_CONTROL_OR_RESET_UNSUPPORTED")
        m=PARAM_OP.fullmatch(stmt)
        param=None
        if m:
            kind,params,operands=m.groups()
            param=[v.strip() for v in params.split(",")]
        else:
            m=OP.fullmatch(stmt)
            if m is None:
                raise VNextError("UNRECOGNISED_QASM_STATEMENT")
            kind,operands=m.groups()
        kind=kind.lower()
        if kind not in MAP:
            raise VNextError("UNSUPPORTED_QASM_GATE:"+kind)
        opcode=MAP[kind]
        expected_params=(3 if kind=="u3" else 1 if kind in
                         ("rz","rx","ry") else 0)
        if (expected_params==0 and param is not None or
            expected_params!=0 and
            (param is None or len(param)!=expected_params)):
            raise VNextError("QASM_GATE_PARAMETER_ARITY")
        refs=[r.strip() for r in operands.split(",")]
        width=2 if opcode in DOUBLE else 1
        if len(refs)!=width:
            raise VNextError("QASM_GATE_QUBIT_ARITY")
        qs=[]
        for ref in refs:
            found=REF.fullmatch(ref)
            if found is None:
                raise VNextError("QASM_WHOLE_REGISTER_GATE_UNSUPPORTED")
            register,integer=found.groups()
            if register not in qregs:
                raise VNextError("QASM_UNKNOWN_QUBIT_REGISTER")
            offset,n_reg=qregs[register]
            qi=int(integer)
            if qi>=n_reg:
                raise VNextError("QASM_GATE_QUBIT_INDEX_OUT_OF_BOUNDS")
            qs.append(offset+qi)
        if len(set(qs))!=width:
            raise VNextError("QASM_GATE_REPEATED_QUBIT")
        if any(q in measures.values() for q in qs):
            raise VNextError("MEASURED_QUBIT_USED_AGAIN")
        if measures:
            deferred_count+=1
        g={"gate":opcode,"qubits":qs}
        if expected_params:
            parsed=[]
            for argument_index,value in enumerate(param):
                approximant,delta=_angle_with_certificate(value)
                parsed.append(approximant)
                if delta:
                    radian_witnesses.append({
                        "statement_index":index,
                        "logical_gate_index":len(gates),
                        "parameter_index":argument_index,
                        "original_decimal_radians":value.strip(),
                        "replacement_rational_pi":approximant,
                        "absolute_angle_error_upper":str(delta),
                        "projective_operator_bound":str(delta/2),
                    })
                    # Rotational gate projective norm is 1-Lipschitz
                    # in half the angular displacement, even for U3.
                    import_projective_bound+=delta/2
            if expected_params==1:
                g["angle_pi"]=parsed[0]
            else:
                g["angles_pi"]=parsed
        gates.append(g)
        if len(gates)>64:
            raise VNextError("QASM_CIRCUIT_EXCEEDS_64_GATE_CERT_SCOPE")
    if not 1<=nq<=4 or nc!=nq:
        raise VNextError("QASM_NONFULL_CLASSICAL_REGISTER")
    if len(measures)!=nq or set(measures)!=set(range(nq)):
        raise VNextError("QASM_NONFULL_MEASUREMENT")
    mapping=[measures[i] for i in range(nq)]
    if len(set(mapping))!=nq:
        raise VNextError("QASM_MEASUREMENT_NOT_BIJECTIVE")
    program=validate_program({"name":name,"qubits":nq,"gates":gates})
    return {
        "schema":"physqed-q-vnext-qasm-import-v1",
        "program":program,
        "classical_output_bit_to_quantum_qubit":mapping,
        "deferred_safe_disjoint_postmeasure_unitaries":deferred_count,
        "source_sha256":hashlib.sha256(text.encode("utf8")).hexdigest(),
        "source_unchanged":True,
        "general_dynamic_circuit_supported":False,
        "decimal_radian_witnesses":radian_witnesses,
        "source_to_rationalpi_projective_bound":str(import_projective_bound),
        "exact_rational_pi_lower":str(PI_LOWER),
        "exact_rational_pi_upper":str(PI_UPPER),
    }
