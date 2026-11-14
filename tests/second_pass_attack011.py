"""Independent group-theoretic verification; no compiler or state simulator import."""
import json
from collections import Counter
from fractions import Fraction
from math import gcd


def order_from_group(a,N):
    if gcd(a,N)!=1:raise ValueError('not a unit')
    x=1
    for r in range(1,N+1):
        x=x*a%N
        if x==1:return r
    raise AssertionError('order not found')


def run():
    generic=0
    spectrum=0
    for N in range(3,101):
        for a in range(2,min(N,14)):
            if gcd(a,N)!=1:continue
            r=order_from_group(a,N)
            for m in range(1,11):
                Q=1<<m
                multiplicities=Counter(pow(a,x,N) for x in range(Q))
                assert len(multiplicities)==min(r,Q)
                assert max(multiplicities.values())-min(multiplicities.values())<=1
                vals=tuple(Fraction(n,Q) for n in multiplicities.values())
                assert sum(vals)==1
                if r & (r-1)==0 and m>=r.bit_length()-1:
                    assert set(vals)=={Fraction(1,r)}
                    spectrum+=1
                generic+=1
    lifting=0
    for s in range(3,91):
        N=1<<s
        r=1<<(s-2)
        assert pow(5,r,N)==1
        assert pow(5,r//2,N)!=1
        lifting+=1
    result={'independent_rank_spectrum_pairs':generic,
            'flat_power_of_two_spectra':spectrum,
            '2_adic_order_instances_s_3_to_90':lifting,
            'verdict':'PASS; representation-only classical lower bound; no Shor QFT'}
    print(json.dumps(result,indent=2))
    return result

if __name__=='__main__':run()
