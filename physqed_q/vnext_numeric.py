"""Independent dense complex-number spot checks for PHYSQED-Q vNext.

No Qiskit/Aer, no fake backend, no external packages.
This independent NUMERICAL oracle is ancillary to the rigorous analytic
rational proof bounds; finite floating-point tests alone are not proof.
"""
import cmath
from fractions import Fraction
import math

from .vnext import rat,validate_program,VNextError


def _matrix(kind, angle=None, angles=None):
    I=1j
    z=lambda x: cmath.exp(I*math.pi*float(x))
    root=math.sqrt(.5)
    if kind=="H":return ((root,root),(root,-root))
    if kind=="X":return ((0,1),(1,0))
    if kind=="Z":return ((1,0),(0,-1))
    if kind=="S":return ((1,0),(0,I))
    if kind=="SDG":return ((1,0),(0,-I))
    if kind=="T":return ((1,0),(0,z(Fraction(1,4))))
    if kind=="TDG":return ((1,0),(0,z(Fraction(-1,4))))
    if kind in {"RZPI","RXPI","RYPI"}:
        t=math.pi*float(rat(angle))
        c=math.cos(t/2)
        s=math.sin(t/2)
        if kind=="RZPI":
            return ((cmath.exp(-I*t/2),0),(0,cmath.exp(I*t/2)))
        if kind=="RXPI":
            return ((c,-I*s),(-I*s,c))
        return ((c,-s),(s,c))
    if kind=="U3PI":
        theta,phi,lam=[math.pi*float(rat(x)) for x in angles]
        c=math.cos(theta/2)
        s=math.sin(theta/2)
        return ((c,-cmath.exp(I*lam)*s),
                (cmath.exp(I*phi)*s,cmath.exp(I*(phi+lam))*c))
    raise VNextError("no single-qubit oracle gate")


def _evolve(program,start):
    n=program["qubits"]
    size=1<<n
    state=[0j]*size
    state[start]=1.+0j
    for op in program["gates"]:
        kind=op["gate"]
        qs=op["qubits"]
        if len(qs)==1:
            q=qs[0]
            mask=1<<q
            m=_matrix(kind,op.get("angle_pi"),op.get("angles_pi"))
            for k in range(size):
                if not k&mask:
                    j=k|mask
                    x=state[k]
                    y=state[j]
                    state[k]=m[0][0]*x+m[0][1]*y
                    state[j]=m[1][0]*x+m[1][1]*y
        elif kind=="CNOT":
            c,t=qs
            for k in range(size):
                if k&(1<<c) and not k&(1<<t):
                    j=k^(1<<t)
                    state[k],state[j]=state[j],state[k]
        elif kind=="CZ":
            a,b=qs
            for k in range(size):
                if k&(1<<a) and k&(1<<b):
                    state[k]=-state[k]
        elif kind=="SWAP":
            a,b=qs
            for k in range(size):
                if k&(1<<a) and not k&(1<<b):
                    j=k^(1<<a)^(1<<b)
                    state[k],state[j]=state[j],state[k]
        else:
            raise VNextError("oracle unsupported two-qubit gate")
    return state


def numeric_unitary(program):
    source=validate_program(program)
    return [_evolve(source,i) for i in range(1<<source["qubits"])]


def frobenius_projective_distance(document):
    """Numerical Frobenius norm after the EXPLICIT certified global phase."""
    source=document["source"];compiled=document["compiled"]
    a=numeric_unitary(source)
    b=numeric_unitary(compiled)
    factor=cmath.exp(1j*math.pi*float(rat(document["global_phase_pi"],
                                          max_abs=1024)))
    squared=0.
    for col_a,col_b in zip(a,b):
        for x,y in zip(col_a,col_b):
            squared+=abs(x-factor*y)**2
    return math.sqrt(squared)


def check_numeric_bound(document, tolerance=2.e-10):
    """Frobenius <= sqrt(2^n)*operator upper bound, a necessary control."""
    fro=frobenius_projective_distance(document)
    logical=float(rat(document["projective_operator_bound"],
                      max_abs=1024))
    worst=math.sqrt(1<<document["source"]["qubits"])*logical
    if fro > worst+tolerance:
        raise VNextError("independent complex matrix violates claimed projective bound")
    return {
        "numeric_frobenius_distance":fro,
        "rational_projective_bound":document["projective_operator_bound"],
        "numeric_implied_frobenius_upper":worst,
        "passes_numeric_control":True,
        "constitutes_formal_interval_proof":False,
    }
