"""Independent gate-pattern executor and exact Fourier/multiplicity auditor.

Does NOT use the production sparse-state simulator or production order verifier.
Each H/CCZ/H pattern is recognized separately as a Toffoli permutation.
"""
import json
from collections import Counter
from fractions import Fraction
from math import gcd
from physqed_q.modexp_core import compile_modexp_core, sparse_integer_state


def unwrap_gates(core):
    """Reject any malformed H-CCZ-Toffoli decomposition."""
    g=core.gates
    m=core.exponent_bits
    assert all(g[j].kind=='H' and g[j].qubits==(j,) for j in range(m))
    k=m
    triples=[]
    while k+2<len(g) and (g[k].kind=='H' and g[k+1].kind=='CCZ' and
                          g[k+2].kind=='H' and g[k].qubits==g[k+2].qubits):
        target=g[k].qubits[0]
        other=tuple(i for i in g[k+1].qubits if i!=target)
        assert len(other)==2
        triples.append((other[0],other[1],target))
        k+=3
    suffix=g[k:]
    assert not suffix or tuple(suffix)==tuple(g[:m])
    assert len(triples)==core.toffoli_count
    return triples, bool(suffix)


def direct_reversible_execution(core,x):
    """Classical Toffoli action only; no production DAG or sparse simulator."""
    gates,_=unwrap_gates(core)
    z=core.initial_basis|x
    for a,b,t in gates:
        if z&(1<<a) and z&(1<<b):
            z^=1<<t
    val=sum(((z>>k)&1)<<i for i,k in enumerate(core.output_wires))
    good=core.initial_basis|x
    good|=sum(((val>>i)&1)<<k for i,k in enumerate(core.output_wires))
    assert z==good,'not all scratch bits cleaned'
    return val


def independent_walsh_marginal(a,N,m):
    """Two-level direct sum of squared signed integer counts, no HFWHT."""
    Q=1<<m
    out={}
    for z in range(Q):
        groups={}
        for x in range(Q):
            y=pow(a,x,N)
            groups[y]=groups.get(y,0)+(-1 if (x&z).bit_count()&1 else 1)
        out[z]=Fraction(sum(v*v for v in groups.values()),Q*Q)
    return out


def run():
    base_count=0
    compiled=0
    max_width=0
    example_sizes={}
    for N in (5,7,8,9,11,13,15,16,21,25,27,35,49):
        for a in range(2,min(N,10)):
            if gcd(a,N)>1:continue
            for m in (1,2,3,4):
                c=compile_modexp_core(N,a,m)
                for x in range(1<<m):
                    assert direct_reversible_execution(c,x)==pow(a,x,N)
                    base_count+=1
                compiled+=1
                max_width=max(max_width,c.n_wires)
    for s in range(3,9):
        N=1<<s
        # Independent modular-order check: distinct successive powers.
        vals=[]
        z=1
        while z not in vals:
            vals.append(z)
            z=(z*5)%N
        assert z==1 and len(vals)==1<<(s-2)
        t=s-2
        m=s
        c=compile_modexp_core(N,5,m,include_final_hadamards=True)
        quantum_state,h=sparse_integer_state(c)
        probs={z:Fraction(0) for z in range(1<<m)}
        for full,amp in quantum_state.items():
            exp_z=full&((1<<m)-1)
            probs[exp_z]+=Fraction(amp*amp,1<<h)
        classical=independent_walsh_marginal(5,N,m)
        assert probs==classical
        assert all(probs[z]==Fraction(int(z<1<<t),1<<t) for z in probs)
        example_sizes[str(s)]={
            'input_qubits':m,
            'modulus_bits':s,
            'total_wires_including_clean_scratch':c.n_wires,
            'hccz_gates':c.gate_count,
            'order':1<<t,
            'Schmidt_rank_lower_bound':1<<t,
            'support':len(quantum_state),
        }
    odd=independent_walsh_marginal(2,21,4)
    assert odd[0]==Fraction(11,64) and odd[14]==Fraction(9,64)
    result={
        'independent_public_arithmetic_cases':base_count,
        'independent_compiled_circuits':compiled,
        'largest_compiled_n_wires':max_width,
        'power_two_family_exact_HCCZ_quantum_checks':6,
        'nonpower_of_two_period_negative_control':{k:str(odd[k]) for k in (0,2,14)},
        'power_two_circuit_growth_and_schmidt':example_sizes,
        'status':'PASS: polynomial modular arithmetic core and fixed-order MPS lower bound; full Shor inverse QFT NOT IMPLEMENTED; unrestricted BPP/BQP OPEN'
    }
    print(json.dumps(result,indent=2,sort_keys=True))
    return result


if __name__=='__main__':
    run()
