"""Independent double-sum (not Walsh) audit of cubic transfer contraction."""
import json
import random
from fractions import Fraction
from physqed_q.cubic_bandwidth import CubicPhase, exact_banded_forrelation, consecutive_cubic_chain


def direct_double_sum(f,g):
    n=f.n
    S=0
    for x in range(1<<n):
        for y in range(1<<n):
            parity=(x&y).bit_count()&1
            S+=1-2*(f.evaluate(x)^g.evaluate(y)^parity)
    return S


def run():
    rng=random.Random(12032026)
    tests=0
    zeros=0
    for n,reps,w in ((1,25,1),(2,40,2),(3,80,3),(4,90,3),
                     (5,70,3),(6,50,4),(7,25,4)):
        masks=[m for m in range(1<<n) if m.bit_count()<=3 and
               (m==0 or m.bit_length()-((m&-m).bit_length()-1)<=w)]
        for _ in range(reps):
            f=CubicPhase(n,tuple(m for m in masks if rng.randrange(2)))
            g=CubicPhase(n,tuple(m for m in masks if rng.randrange(2)))
            out=exact_banded_forrelation(f,g)
            direct=direct_double_sum(f,g)
            assert out.signed_sum==direct,(n,f,g,out.signed_sum,direct)
            assert out.squared_amplitude==Fraction(direct**2,1<<(3*n))
            tests+=1
            zeros+=(direct==0)
    chain={}
    for n in (3,4,5,6,8,10,12,24,48,96,192):
        p=consecutive_cubic_chain(n)
        out=exact_banded_forrelation(p,p)
        chain[str(n)]={"signed_sum":str(out.signed_sum),
                       "probability":str(out.squared_amplitude),
                       "max_states":out.max_active_states}
    return dict(independent_double_sum_cases=tests,zero_cases=zeros,chain=chain,
                verdict="EXACT_REPLAY_PASS, NO_BPP_BQP_SEPARATION")


if __name__=="__main__":
    print(json.dumps(run(),indent=2))
