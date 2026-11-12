"""Clean-room rank-matrix and Walsh audit for quadratic Forrelation.

Separate F_2 Gaussian row reduction from the implementation's Gauss sum.
"""
import json
import random
from fractions import Fraction
from physqed_q.quadratic_forrelation import QuadraticPhase, exact_forrelation, independent_walsh_sum


def polar_matrix(phase_f, phase_g):
    n=phase_f.n
    rows=[0]*(2*n)
    def edge(i,j):
        rows[i]^=1<<j
        rows[j]^=1<<i
    for i in range(n):
        edge(i,n+i)
    for i,j in phase_f.pairs:
        edge(i,j)
    for i,j in phase_g.pairs:
        edge(n+i,n+j)
    return rows


def rank_mod2(rows,columns):
    a=rows[:]
    pivot=0
    for j in range(columns):
        hit=next((r for r in range(pivot,len(a)) if (a[r]>>j)&1),None)
        if hit is None:
            continue
        a[pivot],a[hit]=a[hit],a[pivot]
        for k in range(len(a)):
            if k!=pivot and ((a[k]>>j)&1):
                a[k]^=a[pivot]
        pivot+=1
        if pivot==len(a):
            break
    return pivot


def fn(n,edges,linear=0,constant=0):
    return QuadraticPhase(n,tuple(edges),linear,constant)


def check():
    total=0
    zero=0
    negative=0
    r=random.Random(20261112)
    for n,tries in ((1,100),(2,200),(3,400),(4,400),(5,300),(6,200),(7,100),(8,80),(12,40)):
        edges=[(i,j) for i in range(n) for j in range(i+1,n)]
        for _ in range(tries):
            f=fn(n,[e for e in edges if r.randrange(2)],r.randrange(1<<n),r.randrange(2))
            g=fn(n,[e for e in edges if r.randrange(2)],r.randrange(1<<n),r.randrange(2))
            out=exact_forrelation(f,g)
            rank=rank_mod2(polar_matrix(f,g),2*n)
            k=2*n-rank
            assert rank%2==0
            assert k==out.radical_dimension
            if n<=8:
                assert independent_walsh_sum(f,g)==out.signed_sum
            assert out.squared_amplitude==(Fraction(1<<k,1<<n) if out.sign else Fraction(0))
            total+=1
            zero+=out.sign==0
            negative+=out.sign<0
    n=3
    edges=[(0,1),(0,2),(1,2)]
    fibres=0
    entries=0
    for a in range(1<<len(edges)):
        for b in range(1<<len(edges)):
            f0=fn(n,[edge for k,edge in enumerate(edges) if (a>>k)&1])
            g0=fn(n,[edge for k,edge in enumerate(edges) if (b>>k)&1])
            k=2*n-rank_mod2(polar_matrix(f0,g0),2*n)
            seen=0
            for fl in range(1<<n):
                for gl in range(1<<n):
                    out=exact_forrelation(fn(n,f0.pairs,fl),fn(n,g0.pairs,gl))
                    if out.sign:
                        seen+=1
                    assert (not out.sign) or out.squared_amplitude==Fraction(1<<k,1<<n)
                    entries+=1
            assert seen==(1<<(2*n-k)), (a,b,k,seen)
            fibres+=1
    return dict(rank_walsh_cases=total,zero_cases=zero,negative_cases=negative,
                exhaustive_three_bit_quadratic_part_fibres=fibres,
                fibre_linear_mask_cases=entries,
                conclusion="all rank, Walsh and fibre-frequency assertions passed")


if __name__=='__main__':
    print(json.dumps(check(),indent=2,sort_keys=True))
