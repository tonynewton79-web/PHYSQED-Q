"""Independent, deliberately exponential direct RSA + Walsh audit."""
import json
import random
from math import gcd

def prime(n):
    return n>=2 and all(n%d for d in range(2,n))

def dot(a,b):
    v=a&b
    p=0
    while v:
        v&=v-1
        p^=1
    return p

def direct_spectrum(bits):
    N=len(bits)
    return [sum(1 if bits[r]==dot(z,r) else -1 for r in range(N))
            for z in range(N)]

def run():
    counts={"moduli":7,"rsa_pairs":0,"all_public_masks":0,
            "direct_delta":0,"noisy_delta":0}
    rng=random.Random(20261112010)
    for p,q in ((3,5),(3,7),(5,7),(5,11),(7,11),(11,13),(11,17)):
        assert prime(p) and prime(q)
        N=p*q
        phi=(p-1)*(q-1)
        e=next(e for e in (3,5,7,11,17,19,65537) if gcd(e,phi)==1)
        d=next(d for d in range(1,phi+1) if (d*e)%phi==1)
        k=N.bit_length()
        for x in range(1,N):
            if gcd(x,N)!=1:continue
            y=pow(x,e,N)
            assert pow(y,d,N)==x
            counts["rsa_pairs"]+=1
            bits=[dot(x,r) for r in range(1<<k)]
            counts["all_public_masks"]+=len(bits)
            if x in (1,2,3,N-1) or x%7==0:
                spec=direct_spectrum(bits)
                assert spec[x]==1<<k and sum(abs(s) for s in spec)==1<<k
                counts["direct_delta"]+=1
                noisy=bits[:]
                m=(1<<k)//5
                for j in rng.sample(range(1<<k),m):noisy[j]^=1
                trial=direct_spectrum(noisy)
                assert trial[x]==(1<<k)-2*m
                assert max(range(1<<k),key=lambda i:abs(trial[i]))==x
                counts["noisy_delta"]+=1
    counts["status"]="PASS: toy arithmetic and exact Fourier only; RSA OW unproved"
    print(json.dumps(counts,indent=2))
    return counts

if __name__=="__main__":
    run()
