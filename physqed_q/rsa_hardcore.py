"""Attack 010: public RSA/Goldreich-Levin hard-core decision benchmark.

CONDITIONAL CLAIM ONLY: RSA classical one-wayness + Shor + GL + H/CCZ
universality. Here we test small RSA, exact Walsh identities and a tiny
H/CCZ phase-kickback control. This is NOT a Shor circuit or BPP/BQP proof.
"""
from dataclasses import dataclass
from fractions import Fraction
from math import gcd, isqrt

@dataclass(frozen=True)
class RSAInput:
    """All four fields are PUBLIC; the factors and inverse are not fields."""
    N: int
    e: int
    y: int
    r: int

    def __post_init__(self):
        if type(self.N) is not int or self.N < 15 or self.N % 2 == 0:
            raise ValueError("N must be odd and >=15")
        if type(self.e) is not int or self.e < 2:
            raise ValueError("e must be >=2")
        if type(self.y) is not int or not 0 <= self.y < self.N:
            raise ValueError("invalid ciphertext")
        if type(self.r) is not int or not 0 <= self.r < 1 << self.k:
            raise ValueError("invalid public mask")

    @property
    def k(self):
        return self.N.bit_length()

def parity_mask(x,mask):
    if type(x) is not int or type(mask) is not int or x<0 or mask<0:
        raise ValueError("nonnegative integer operands required")
    return (x&mask).bit_count()&1

def _prime_small(n):
    if n<2:return False
    for d in range(2,isqrt(n)+1):
        if n%d==0:return False
    return True

def _toy_factors(N):
    """Non-scalable, intentionally capped classical reference."""
    if type(N) is not int or not 15<=N<=65535:
        raise ValueError("toy factoring refuses >16 bits")
    for p in range(3,isqrt(N)+1,2):
        if N%p==0:
            q=N//p
            if p!=q and _prime_small(p) and _prime_small(q):
                return p,q
    return None

def public_bit_toy(instance):
    """Total language on tiny supported inputs only; NOT a scalable solver."""
    if not isinstance(instance,RSAInput):
        raise TypeError("RSAInput required")
    pair=_toy_factors(instance.N)
    if pair is None:return 0
    p,q=pair
    phi=(p-1)*(q-1)
    if gcd(instance.e,phi)!=1 or gcd(instance.y,instance.N)!=1:
        return 0
    d=pow(instance.e,-1,phi)
    x=pow(instance.y,d,instance.N)
    if pow(x,instance.e,instance.N)!=instance.y:
        raise AssertionError("inconsistent inversion")
    return parity_mask(x,instance.r)

def toy_fixture(p,q,e,x,r):
    """Private factors occur in TEST GENERATION, not the public instance."""
    if any(type(z) is not int for z in (p,q,e,x,r)):
        raise ValueError("all parameters must be integers")
    if not (_prime_small(p) and _prime_small(q) and p!=q and p%2 and q%2):
        raise ValueError("two distinct odd primes required")
    N=p*q
    if N>65535 or not 1<=x<N or gcd(x,N)!=1:
        raise ValueError("invalid tiny secret")
    if e<2 or gcd(e,(p-1)*(q-1))!=1:
        raise ValueError("invalid RSA exponent")
    public=RSAInput(N,e,pow(x,e,N),r)
    return public,parity_mask(x,r)

def brute_inverse_toy(instance):
    """Exhaustive classical inversion, exponential in input bit count."""
    if instance.k>16:raise ValueError("refuse large-instance brute force")
    matches=[x for x in range(1,instance.N)
             if gcd(x,instance.N)==1 and pow(x,instance.e,instance.N)==instance.y]
    return matches[0] if len(matches)==1 else None

def hadamard_spectrum_of_bit_oracle(bits):
    """Exponential table, exact Walsh: NOT the efficient GL list decoder."""
    N=len(bits)
    if N<2 or (N&(N-1)) or N>4096:
        raise ValueError("power-of-two table 2..4096 required")
    if any(type(b) is not int or b not in (0,1) for b in bits):
        raise ValueError("binary output required")
    out=[1-2*b for b in bits]
    h=1
    while h<N:
        for start in range(0,N,2*h):
            for i in range(start,start+h):
                a,b=out[i],out[i+h]
                out[i],out[i+h]=a+b,a-b
        h*=2
    if sum(z*z for z in out)!=N*N:raise AssertionError("Parseval")
    return tuple(out)

def ideal_mask_truth_table(x,k):
    if type(k) is not int or not 1<=k<=12 or type(x) is not int or not 0<=x<1<<k:
        raise ValueError("finite diagnostic only")
    return tuple(parity_mask(x,r) for r in range(1<<k))

def finite_walsh_recover(bits):
    """Return the leading Fourier frequency: exhaustive, NOT polynomial time."""
    freq=hadamard_spectrum_of_bit_oracle(bits)
    idx=max(range(len(freq)),key=lambda i:abs(freq[i]))
    return idx,Fraction(freq[idx],len(bits))

def hccz_phase_kickback_control():
    """Actual 3-wire quantum interference, not RSA factoring or Shor.

    Control=0, orbit=1, fixed-|1> ancilla=2. With orbit |- >, the control
    deterministically becomes |1>; with orbit |+> it becomes |0>.
    """
    from .hccz_circuit import Gate
    gates=(Gate('H',(1,)),Gate('H',(0,)),Gate('H',(1,)),
           Gate('CCZ',(0,1,2)),Gate('H',(1,)),Gate('H',(0,)))
    return 3,gates
