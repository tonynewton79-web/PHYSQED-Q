"""Independent integer audit, avoiding the implementation's sign/moment routines."""
import json
import math
from fractions import Fraction
from physqed_q.dense_bent import direct_p, direct_g, make_pair
from physqed_q.cubic_bandwidth import independent_walsh_sum
from physqed_q.path_sampling_gate import (
    certify_dense_pair, hccz_forrelation_program, exact_sign_only_chi_squared,
)


def direct_path_sum(r, tilt):
    n=4*r
    N=1<<n
    # No Walsh transform: independent O(2^(2n)) signed double sum.
    f=[direct_p(r,x) for x in range(N)]
    g=[direct_g(r,y,tilt=tilt) for y in range(N)]
    counts=[0,0]
    for x in range(N):
        fx=f[x]
        for y in range(N):
            z=fx ^ g[y] ^ ((x&y).bit_count()&1)
            counts[z]+=1
    return counts[0]-counts[1],counts


def sign_only_total_variation_integer(n, m):
    """Exact TV between m sign-only YES and NO observations, n multiple of 4."""
    if n%2:
        raise ValueError('even n required')
    e=1<<(n//2)
    a,b=e+1,e-1
    base=2*e
    delta=sum(math.comb(m,k)*abs(pow(a,k)*pow(b,m-k)-pow(e,m))
              for k in range(m+1))
    return Fraction(delta,2*pow(base,m))


def first_samples_at_two_thirds(n, horizon):
    for m in range(horizon+1):
        tv=sign_only_total_variation_integer(n,m)
        if tv>=Fraction(1,3):
            return m,tv
    return None,None


def run():
    raw={}
    for t in (0,1,3,255):
        S,counts=direct_path_sum(2,t)
        c=certify_dense_pair(2,tilt=t)
        assert S==c.forrelation_numerator
        assert Fraction(counts[0],1<<16)==c.path_sign_plus_probability
        raw[str(t)]={'sum':S,'positive':counts[0],'negative':counts[1]}

    mask_walsh=0
    for t in (0,1,2,8,31,63,2048,4095):
        f,g=make_pair(3,tilt=t)
        assert independent_walsh_sum(f,g)==(1<<18 if t==0 else 0)
        mask_walsh+=1

    tested=0
    for n in (4,8,12):
        for m in (0,1,2,3,5,10,20,32,64,96,128):
            tv=sign_only_total_variation_integer(n,m)
            chi=exact_sign_only_chi_squared(n,m)
            assert 4*tv*tv <= chi
            tested+=1
    m_star,tv_star=first_samples_at_two_thirds(8,400)
    assert m_star is not None
    assert sign_only_total_variation_integer(8,m_star-1)<Fraction(1,3)
    assert tv_star>=Fraction(1,3)

    sizes=[]
    for r in (2,3,4,8,12,20):
        wires,basis,gates,flip=hccz_forrelation_program(r)
        assert wires==4*r+2 and flip==1
        assert sum(g.kind=='H' for g in gates)==12*r
        assert all(g.kind in ('H','CCZ') for g in gates)
        sizes.append({'r':r,'data_qubits':4*r,'gates':len(gates)})
    return {'direct_paths':raw,
            'independent_walsh_12bit_tilts':mask_walsh,
            'exact_tv_chi_squared_pairs':tested,
            'n8_minimum_sign_only_iid_samples_to_get_bayes_success_2_3':m_star,
            'n8_tv_at_threshold':str(tv_star),
            'circuit_sizes':sizes,
            'verdict':'PASS: restricted estimator lower bound; EXPLICIT FAMILY IN P; BPP vs BQP OPEN'}


if __name__=='__main__':
    print(json.dumps(run(),indent=2))
