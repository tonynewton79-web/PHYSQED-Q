"""Independent direct-double-sum and Boolean identity audit.

Exponential test is deliberately capped at n<=7; not a scalable solver.
"""
import json
import random
from itertools import combinations
from physqed_q.cubic_slice import Phase, complete_cubic, exact_forrelation


def direct_anf(terms, z):
    return sum((z & mask) == mask for mask in terms) & 1


def direct_sum(p, q):
    S=0
    terms_p=p.expanded_anf()
    terms_q=q.expanded_anf()
    for x in range(1<<p.n):
        for y in range(1<<p.n):
            sign = direct_anf(terms_p,x) ^ direct_anf(terms_q,y)
            sign ^= (x&y).bit_count()&1
            S += 1-2*sign
    return S


def gl_scramble(n,rng):
    """Upper-triangular invertible binary linear map, y_i = row_i . x."""
    rows = [(1<<i) | sum((rng.randrange(2)<<j) for j in range(i+1,n)) for i in range(n)]
    linear = 0
    qterms = set()
    for row in rows:
        linear ^= row
    for i,j in combinations(range(n),2):
        ai,aj=rows[i],rows[j]
        for x in range(n):
            if ai & (1<<x):
                for y in range(n):
                    if aj & (1<<y):
                        mask = (1<<x)|(1<<y)
                        if mask in qterms: qterms.remove(mask)
                        else: qterms.add(mask)
    return rows,Phase(n, factors=((linear,tuple(sorted(qterms))),))


def run():
    rng=random.Random(202611120505)
    direct_count=0
    scramble_count=0
    for n,tries in ((2,25),(3,40),(4,55),(5,50),(6,30),(7,15)):
        masks=[t for t in range(1<<n) if t.bit_count()<=2]
        def random_phase():
            base=tuple(t for t in masks if rng.randrange(2))
            factors=tuple((rng.randrange(1,1<<n),tuple(t for t in masks if rng.randrange(2)))
                          for _ in range(rng.randrange(3)))
            return Phase(n,base,factors)
        for _ in range(tries):
            p,q=random_phase(),random_phase()
            cert=exact_forrelation(p,q)
            direct=direct_sum(p,q)
            assert cert.signed_sum==direct
            direct_count+=1
    for n in range(3,11):
        for _ in range(15):
            rows,p=gl_scramble(n,rng)
            for x in range(1<<n):
                y=sum(((x&row).bit_count()&1)<<i for i,row in enumerate(rows))
                expected = y.bit_count()%4 == 3
                assert p.evaluate(x) == expected
                assert direct_anf(p.expanded_anf(),x) == expected
                scramble_count+=1
    return dict(direct_double_sum_cases=direct_count,
                scrambled_anf_input_checks=scramble_count,
                dense_complete_hypergraph_n72={
                    'monomials':72*71*70//6,'min_hitting_set':70,
                    'primal_treewidth':71,
                    'gaussian_branches':exact_forrelation(complete_cubic(72),complete_cubic(72)).gaussian_branches},
                status='PASS_NO_CLASS_SEPARATION')


if __name__=='__main__':
    print(json.dumps(run(),indent=2))
