"""PHYSQED-Q Attack 012: exact real H/CCZ general-order Fourier MEASUREMENT.

Kitaev X/Y tests, one shared rebit and a clean reversible modexp network.
NOT a native coherent inverse-QFT gate synthesis. The truncated coherent
IQFT planner is an ABSTRACT IR and explicitly refuses native completeness.
"""
from dataclasses import dataclass
from fractions import Fraction
from math import gcd,ceil,log,atan2,cos,sin,pi,sqrt
import random

from .modexp_core import _Builder,Gate,ModexpCore,sparse_integer_state


@dataclass(frozen=True)
class FourierStage:
    modulus:int
    base:int
    phase_bits:int
    repeats:int
    target_wires:tuple[int,...]
    rebit_wire:int
    fixed_one_wire:int
    n_wires:int
    initial_basis:int
    gates:tuple[Gate,...]
    x_controls:tuple[tuple[int,...],...]
    y_controls:tuple[tuple[int,...],...]
    work_wires:tuple[int,...]
    modexp_gate_count:int


def _compile_toffoli(gates):
    out=[]
    for g in gates:
        if g.kind=="H":
            out.append(g)
        elif g.kind=="TOFFOLI":
            a,b,t=g.qubits
            out.extend((Gate("H",(t,)),Gate("CCZ",(a,b,t)),Gate("H",(t,))))
        else:
            raise AssertionError("unexpected gate")
    return tuple(out)


def _realified_s_dagger(control,rebit,one):
    """S† is conditional ZX on the shared real-imaginary encoding rebit."""
    return (Gate("H",(rebit,)),Gate("CCZ",(control,rebit,one)),
            Gate("H",(rebit,)),Gate("CCZ",(control,rebit,one)))


def compile_fourier_measurement(modulus:int,base:int,phase_bits:int,repeats:int=1)->FourierStage:
    """Uniform polynomial-size exact H/CCZ compiler for X/Y phase tests.

    One common target orbit, not independent targets across repetitions.
    """
    if (type(modulus) is not int or modulus<3 or type(base) is not int
        or not 1<base<modulus or gcd(base,modulus)!=1
        or type(phase_bits) is not int or phase_bits<1
        or type(repeats) is not int or repeats<1):
        raise ValueError("N>=3, invertible 1<a<N, m>=1, t>=1 required")
    C=2*phase_bits*repeats
    s=modulus.bit_length()
    b=_Builder(C,s)
    xs=[];ys=[]
    cur=(b.one,)+(b.zero,)*(s-1)
    for j in range(phase_bits):
        xgroup=tuple(range(2*repeats*j,2*repeats*j+repeats))
        ygroup=tuple(range(2*repeats*j+repeats,2*repeats*(j+1)))
        xs.append(xgroup);ys.append(ygroup)
        factor=pow(base,1<<j,modulus)
        for control in xgroup+ygroup:
            mult=b.mul_mod(cur,factor,modulus)
            cur=tuple(b.mux(control,mult[i],cur[i]) for i in range(s))
    reversible=b.reversible_gates(cur)
    start=tuple(Gate("H",(j,)) for j in range(C))
    core=_compile_toffoli(start+reversible)
    rebit=b.next
    measure=[]
    for group in xs:
        measure.extend(Gate("H",(c,)) for c in group)
    for group in ys:
        for c in group:
            measure.extend(_realified_s_dagger(c,rebit,b.one))
            measure.append(Gate("H",(c,)))
    gates=core+tuple(measure)
    assert all(g.kind in ("H","CCZ") for g in gates)
    return FourierStage(modulus,base,phase_bits,repeats,b.output,rebit,b.one,
                        b.next+1,(1<<b.one)|(1<<b.one_second),gates,
                        tuple(xs),tuple(ys),
                        tuple(range(C+3+s,b.next)),len(core))


def sparse_fourier_measurement_state(stage,maximum_support=1<<15):
    """Exact bounded physical verifier: returns control-outcome probabilities."""
    core=ModexpCore(stage.modulus,stage.base,2*stage.phase_bits*stage.repeats,
                    stage.modulus.bit_length(),stage.n_wires,
                    stage.initial_basis,stage.target_wires,stage.work_wires,
                    len(stage.gates),sum(g.kind=="CCZ" for g in stage.gates),
                    sum(g.kind=="H" for g in stage.gates),stage.gates)
    states,h=sparse_integer_state(core,maximum_support=maximum_support)
    outcome={}
    controls=(1<<(2*stage.phase_bits*stage.repeats))-1
    for z,amp in states.items():
        used=stage.initial_basis|(z&controls)|(((z>>stage.rebit_wire)&1)<<stage.rebit_wire)
        used|=sum(((z>>wire)&1)<<wire for wire in stage.target_wires)
        if used!=z:raise AssertionError("work/ancilla leakage")
        key=z&controls
        outcome[key]=outcome.get(key,0)+amp*amp
    return {k:Fraction(v,1<<h) for k,v in outcome.items()}


def independent_mixture_probability(stage,outcome):
    """Small-order analytical check, NOT a scalable sampling algorithm."""
    from .modexp_core import order_toy
    r=order_toy(stage.base,stage.modulus)
    total=0.0
    for ell in range(r):
        p=1.0
        for j in range(stage.phase_bits):
            angle=2*pi*((ell*(1<<j))%r)/r
            px=(1+cos(angle))/2
            py=(1+sin(angle))/2
            for c in stage.x_controls[j]:
                p*=px if not (outcome>>c)&1 else 1-px
            for c in stage.y_controls[j]:
                p*=py if not (outcome>>c)&1 else 1-py
        total+=p
    return total/r


def required_repeats(phase_bits:int,failure_probability:Fraction)->int:
    """Exact Hoeffding budget: t=128 ceil(log2(4m/delta))."""
    if type(phase_bits) is not int or phase_bits<1:
        raise ValueError("m must be positive")
    if not isinstance(failure_probability,Fraction) or not 0<failure_probability<1:
        raise ValueError("delta must be a rational in (0,1)")
    q=Fraction(4*phase_bits,1)/failure_probability
    k=max(0,q.numerator.bit_length()-q.denominator.bit_length())
    while (1<<k)*q.denominator<q.numerator:k+=1
    while k>0 and (1<<(k-1))*q.denominator>=q.numerator:k-=1
    return 128*k


def sample_hidden_eigenphase(modulus,base,phase_bits,repeats,rng,hidden_phase=None):
    """Independent reference sampler. Hidden order used ONLY in the test harness."""
    from .modexp_core import order_toy
    r=order_toy(base,modulus)
    ell=rng.randrange(r) if hidden_phase is None else hidden_phase
    if not 0<=ell<r:raise ValueError("invalid hidden eigenphase")
    xs=[];ys=[]
    for j in range(phase_bits):
        angle=2*pi*((ell*(1<<j))%r)/r
        px=(1+cos(angle))/2
        py=(1+sin(angle))/2
        xs.append([int(rng.random()>=px) for _ in range(repeats)])
        ys.append([int(rng.random()>=py) for _ in range(repeats)])
    return ell,xs,ys


def factoring_from_order(N,a,r):
    if r is None or r<=0 or r%2:return None
    y=pow(a,r//2,N)
    if y in (1,N-1):return None
    p=gcd(y-1,N);q=gcd(y+1,N)
    if 1<p<N and N%p==0:return tuple(sorted((p,N//p)))
    if 1<q<N and N%q==0:return tuple(sorted((q,N//q)))
    return None


def decode_native_measurement(stage,measured_controls):
    """Public exact-rational decoding of one actual H/CCZ control measurement."""
    from .certified_phase_decode import (
        reconstruct_phase_exact,recover_order_from_exact_phase)
    C=2*stage.phase_bits*stage.repeats
    if (not isinstance(stage,FourierStage) or
        type(measured_controls) is not int or not 0<=measured_controls<(1<<C)):
        raise ValueError("invalid native Fourier readout")
    xs=[[((measured_controls>>c)&1) for c in g] for g in stage.x_controls]
    ys=[[((measured_controls>>c)&1) for c in g] for g in stage.y_controls]
    theta=reconstruct_phase_exact(xs,ys)
    order=recover_order_from_exact_phase(theta,stage.modulus,stage.base)
    return {"phase":theta,"order":order,
            "factors":factoring_from_order(stage.modulus,stage.base,order)}


@dataclass(frozen=True)
class AbstractIQFTPlan:
    """The retained controlled phase rotations are NOT compiled to H/CCZ."""
    n_qubits:int
    cutoff:int
    requested_operator_error:Fraction
    omitted_rotation_upper_bound:Fraction
    per_retained_rotation_budget:Fraction
    retained_rotation_count:int
    gates:tuple[tuple[str,tuple[int,...],int],...]
    exact_hccz_compiler_available:bool=False


def abstract_inverse_qft(n:int,epsilon:Fraction)->AbstractIQFTPlan:
    """Abstract unitary IQFT with rigorous m*pi/2^K + M*eta norm budget."""
    if type(n) is not int or n<1 or not isinstance(epsilon,Fraction) or not 0<epsilon<=1:
        raise ValueError("n>=1, 0<eps<=1 exact rational required")
    k=0
    while Fraction(22*n,7*(1<<k))>epsilon/2:k+=1
    gates=[]
    for j in range(n//2):gates.append(("SWAP",(j,n-1-j),0))
    count=0
    for j in range(n):
        for lower in range(j):
            d=j-lower
            if d<=k:
                gates.append(("CP",(j,lower),d))
                count+=1
        gates.append(("H",(j,),0))
    omitted=Fraction(22*n,7*(1<<k))
    per=epsilon/(2*max(1,count))
    assert omitted<=epsilon/2 and omitted+count*per<=epsilon
    return AbstractIQFTPlan(n,k,epsilon,omitted,per,count,tuple(gates),False)


def simulate_inverse_qft_ir(plan:AbstractIQFTPlan):
    """Standard-library finite complex reference; NOT H/CCZ compilation."""
    n=plan.n_qubits
    if n>7:raise ValueError("matrix verifier limited to n<=7")
    L=1<<n
    out=[[complex(i==j) for j in range(L)] for i in range(L)]
    for kind,qs,d in plan.gates:
        if kind=="SWAP":
            a,b=qs
            for x in range(L):
                if ((x>>a)&1)^((x>>b)&1):
                    y=x^((1<<a)|(1<<b))
                    if y>x:out[x],out[y]=out[y],out[x]
        elif kind=="CP":
            a,b=qs
            angle=-pi/(1<<d)
            factor=complex(cos(angle),sin(angle))
            for x in range(L):
                if (x>>a)&1 and (x>>b)&1:
                    out[x]=[z*factor for z in out[x]]
        elif kind=="H":
            a=qs[0];bit=1<<a
            for x in range(L):
                if x&bit:continue
                v=out[x][:];w=out[x|bit][:]
                out[x]=[(p+q)/sqrt(2) for p,q in zip(v,w)]
                out[x|bit]=[(p-q)/sqrt(2) for p,q in zip(v,w)]
        else:raise AssertionError("unknown abstract gate")
    return tuple(tuple(row) for row in out)
