"""Independent public CNF census and exact interference audit.

Counts CNF truth tables independently of the module's sat_count helper.
"""
import json
from fractions import Fraction
from itertools import product
from physqed_q.sat_interference import (
    compile_cnf, direct_phase_gap, constraint_pairing_gap,
    recover_count_from_probability, hccz_program,
    additive_probability_approximation,
)


def independent_count(n,formula):
    total=0
    for bits in product((False,True),repeat=n):
        satisfied=True
        for clause in formula:
            if not any(bits[abs(l)-1] if l>0 else not bits[abs(l)-1]
                       for l in clause):
                satisfied=False
                break
        if satisfied:
            total+=1
    return total


def run():
    options=((1,),(-1,),(2,),(-2,),
             (1,2),(1,-2),(-1,2),(-1,-2))
    tested=0
    direct=0
    unsat=0
    hist={}
    max_N=0
    for k in (1,2,3):
        for formula in product(options,repeat=k):
            s=independent_count(2,formula)
            r=compile_cnf(2,formula)
            S=s<<r.constraint_bits
            assert constraint_pairing_gap(r)==S
            if r.phase_bits<=13:
                assert direct_phase_gap(r)==S
                direct+=1
            p=Fraction(s*s,1<<(2*(2+r.work_bits)))
            assert recover_count_from_probability(r,p)==s
            wires,basis,gates,sign=hccz_program(r)
            assert wires==r.phase_bits+2
            assert basis==3<<r.phase_bits
            assert sum(kind=="H" for kind,_ in gates)==2*r.phase_bits
            assert all(kind in ("H","CCZ") for kind,_ in gates)
            assert all(mask.bit_count()<=3 for mask in r.phase_monomials)
            tested+=1
            unsat+=(s==0)
            hist[s]=hist.get(s,0)+1
            max_N=max(max_N,r.phase_bits)
    for n in range(1,33):
        r=compile_cnf(n,tuple((j,) for j in range(1,n+1)))
        assert r.work_bits==n-1
        assert r.phase_bits==3*n-1
        assert r.predicted_probability(1)==Fraction(1,1<<(4*n-2))
        eps=Fraction(1,100)
        a=additive_probability_approximation(r,eps)
        assert abs(a.estimate-r.predicted_probability(1))<=a.maximum_absolute_error
        assert a.maximum_absolute_error<=eps
    return {
        "public_CNF_instances":tested,
        "signed_phase_sums":direct,
        "unsatisfiable_instances":unsat,
        "satisfying_count_histogram":hist,
        "largest_phase_bits":max_N,
        "unique_sat_asymptotic_checks":32,
        "verdict":"EXACT_COUNTING_PASS; ADDITIVE_FPTAS_PASS; BPP_VS_BQP_OPEN",
    }


if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True))
