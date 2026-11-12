"""Independent direct Fourier-dual audit, outside the promise classifier."""
from random import Random
import json
from physqed_q.dense_bent import (
    make_pair, pi_involution, quadratic_controls, all_linear_tilt_numerators,
)


def dot(x,y):
    return (x&y).bit_count()&1


def run():
    rng=Random(261111204)
    coeff_checks=fourier_checks=involution_checks=0
    for r,freq_count in ((2,None),(3,40),(4,8)):
        n=4*r
        half=2*r
        limit=1<<half
        p,g=make_pair(r)
        frequencies=(range(1<<n) if freq_count is None else
                     [rng.randrange(1<<n) for _ in range(freq_count)])
        for freq in frequencies:
            u,v=freq&(limit-1),freq>>half
            predicted=(1<<half)*(-1 if dot(v,pi_involution(r,u)) else 1)
            direct=sum(-1 if (p.evaluate(z)^dot(z,freq)) else 1
                       for z in range(1<<n))
            assert direct==predicted
            assert (1-2*g.evaluate(freq))*(1<<half)==direct
            fourier_checks+=1
        for _ in range(250):
            y=rng.randrange(limit)
            assert pi_involution(r,pi_involution(r,y))==y
            involution_checks+=1
        for pairs in quadratic_controls(r):
            assert all(0<=i<k<r for i,k in pairs)
            coeff_checks+=len(pairs)
    p,g=make_pair(2)
    nums=all_linear_tilt_numerators(p,g)
    assert nums[0]==(1<<12) and all(s==0 for s in nums[1:])
    assert sum(s*s for s in nums)==(1<<24)
    return dict(
        fourier_coefficients_exactly_checked=fourier_checks,
        involution_cases_checked=involution_checks,
        cubic_monomial_occurrences_checked=coeff_checks,
        complete_linear_mask_orbit=256,
        verdict="PASS (known Maiorana-McFarland construction; no class separation)",
    )


if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True))
