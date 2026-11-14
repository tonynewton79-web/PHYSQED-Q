"""Independent exact Gaussian-integer path sum, no latent-phase/QFT formulas."""
import json
import random
from math import gcd
from fractions import Fraction
from physqed_q.fourier_stage import (
    compile_fourier_measurement,sparse_fourier_measurement_state,
    sample_hidden_eigenphase,required_repeats,factoring_from_order,
    decode_native_measurement,
)
from physqed_q.certified_phase_decode import (
    reconstruct_phase_exact,recover_order_from_exact_phase,
)


def direct_fourier_integer_distribution(N,a,m,t):
    """Exactly 4^C Gaussian integer operations, C=2*m*t (tiny reference)."""
    C=2*m*t
    if C>10:raise ValueError("independent direct reference <=10 controls")
    X=1<<C
    powers=[];ymask=0
    for j in range(m):
        for rep in range(t):powers.append(1<<j)
        for rep in range(t):
            index=len(powers)
            powers.append(1<<j)
            ymask|=1<<index
    outputs=[]
    for b in range(X):
        exponent=sum(powers[j] for j in range(C) if (b>>j)&1)
        outputs.append(pow(a,exponent,N))
    probs={}
    for z in range(X):
        groups={}
        for b,y in enumerate(outputs):
            k=(b&ymask).bit_count()%4
            re,im=((1,0),(0,-1),(-1,0),(0,1))[k]
            if (b&z).bit_count()%2:re=-re;im=-im
            u,v=groups.get(y,(0,0))
            groups[y]=(u+re,v+im)
        probs[z]=Fraction(sum(u*u+v*v for u,v in groups.values()),X*X)
    assert sum(probs.values())==1
    return probs


def run():
    configs=((5,2,1,1),(7,2,1,1),(9,2,2,1),(15,2,2,1),
             (21,2,2,1),(21,2,3,1),(21,2,2,2),(35,2,1,1),(15,2,5,1))
    count={'full_physical_distributions':0,'exact_outcome_probabilities':0,
           'exact_clean_work_checks':0,'native_gate_count':0}
    for N,a,m,t in configs:
        direct=direct_fourier_integer_distribution(N,a,m,t)
        stage=compile_fourier_measurement(N,a,m,t)
        physical=sparse_fourier_measurement_state(stage)
        assert all(physical.get(z,0)==direct[z] for z in direct)
        assert all(g.kind in ('H','CCZ') for g in stage.gates)
        count['full_physical_distributions']+=1
        count['exact_outcome_probabilities']+=len(direct)
        count['exact_clean_work_checks']+=1
        count['native_gate_count']+=len(stage.gates)

    stage=compile_fourier_measurement(15,2,5,1)
    distribution=sparse_fourier_measurement_state(stage)
    factors=Fraction(0)
    for z,p in distribution.items():
        decoded=decode_native_measurement(stage,z)
        if decoded['factors'] is not None:
            assert decoded['order']==4 and decoded['factors']==(3,5)
            factors+=p
    assert factors==Fraction(1,2)
    count['native_full_factor15_probability']=str(factors)

    rng=random.Random(20261114012012)
    result={}
    for N,a,r in ((15,2,4),(21,2,6),(35,2,12)):
        m=2*N.bit_length()+2
        t=required_repeats(m,Fraction(1,20))
        success=0;coprime=0;failures=0
        for trial in range(150):
            hidden,x,y=sample_hidden_eigenphase(N,a,m,t,rng)
            theta=reconstruct_phase_exact(x,y)
            found=recover_order_from_exact_phase(theta,N,a)
            good=(gcd(hidden,r)==1)
            if good:coprime+=1
            if found==r:
                success+=1
                assert factoring_from_order(N,a,found) is not None
            elif good:failures+=1
        assert failures==0 and success>=22
        result[str(N)]={'r_REFERENCE_ONLY':r,'trials':150,'exact_order_factors':success,
                        'coprime_latent':coprime,'conditional_failures':failures,
                        'm':m,'certified_repeats':t}
    count['analytic_reference_trials']=450
    count['analytical_reference_results']=result
    count['status']="PASS: exact native measurement alternative; coherent IQFT CP synthesis OPEN; BPP vs BQP OPEN"
    return count


if __name__=='__main__':
    print(json.dumps(run(),indent=2))
