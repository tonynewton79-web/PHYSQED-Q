"""Exact-integer X/Y quadrature phase reconstruction (PHYSQED-Q Attack 012).

Certified 64-root table: Machin arctan bounds, Taylor bounds, 24-bit integer
dot products. Exact rational phase unwrapping and continued fractions.
"""
from fractions import Fraction
from functools import lru_cache
from math import factorial,gcd


def _atan_interval_inverse(q:int,terms:int=30):
    if q<=1 or terms<2:raise ValueError("q>1 and terms>=2")
    total=sum((Fraction(1,(2*j+1)*q**(2*j+1)) if j%2==0
               else -Fraction(1,(2*j+1)*q**(2*j+1))) for j in range(terms))
    nxt=Fraction(1,(2*terms+1)*q**(2*terms+1))
    return (total,total+nxt) if terms%2==0 else (total-nxt,total)


def rational_pi_interval():
    a,b=_atan_interval_inverse(5)
    c,d=_atan_interval_inverse(239)
    lower=16*a-4*d
    upper=16*b-4*c
    assert 3<lower<upper<Fraction(22,7)
    return lower,upper


def _taylor_cos(x,terms=16):
    return sum(Fraction((-1)**j,factorial(2*j))*x**(2*j)
               for j in range(terms+1))


def _taylor_sin(x,terms=16):
    return sum(Fraction((-1)**j,factorial(2*j+1))*x**(2*j+1)
               for j in range(terms+1))


def _round_rational_integer(x):
    return (2*x.numerator+x.denominator)//(2*x.denominator)


@lru_cache(maxsize=1)
def certified_unit_circle_grid():
    """64 integer vectors scaled by 2^24; component error <2^-22."""
    p_lo,p_hi=rational_pi_interval()
    p=(p_lo+p_hi)/2
    width=p_hi-p_lo
    terms=16
    sin_remainder=p_hi**(2*terms+3)/factorial(2*terms+3)
    cos_remainder=p_hi**(2*terms+2)/factorial(2*terms+2)
    size=1<<24
    output=[]
    for k in range(64):
        signed=k if k<=32 else k-64
        x=p*Fraction(signed,32)
        c=_taylor_cos(x,terms)
        s=_taylor_sin(x,terms)
        cn=_round_rational_integer(c*size)
        sn=_round_rational_integer(s*size)
        e=width+max(sin_remainder,cos_remainder)+Fraction(1,2*size)
        assert e<Fraction(1,1<<22)
        output.append((cn,sn))
    assert output[0]==(size,0)
    assert output[16]==(0,size)
    assert output[32]==(-size,0)
    assert output[48]==(0,-size)
    return tuple(output)


def binary_quadrature_phase(xs,ys):
    """Return nearest of 64 roots using exact integer dot products."""
    if not isinstance(xs,(list,tuple)) or not isinstance(ys,(list,tuple)):
        raise ValueError("binary X/Y sequences required")
    if len(xs)<1 or len(ys)<1 or len(xs)!=len(ys):
        raise ValueError("positive equal repeats required")
    if any(type(z) is not int or z not in (0,1) for z in xs+ys):
        raise ValueError("binary measurement outcomes required")
    c=sum(1-2*z for z in xs)
    s=sum(1-2*z for z in ys)
    if c==0 and s==0:
        raise ValueError("ambiguous phase vector; quadrature promise failed")
    grid=certified_unit_circle_grid()
    return max(range(64),key=lambda k:grid[k][0]*c+grid[k][1]*s)


def _circular_fraction_distance(x,y):
    d=(x-y)%1
    return min(d,1-d)


def reconstruct_phase_exact(x_samples,y_samples):
    """All-size good-event error < 1/(16*2^(m-1)), exact rational result."""
    if (not isinstance(x_samples,(list,tuple)) or
        not isinstance(y_samples,(list,tuple)) or
        not x_samples or len(x_samples)!=len(y_samples)):
        raise ValueError("equal nonempty phase sequences required")
    roots=[binary_quadrature_phase(tuple(x),tuple(y))
           for x,y in zip(x_samples,y_samples)]
    phase=Fraction(roots[-1],64)
    for k in reversed(roots[:-1]):
        a=phase/2
        b=(phase+1)/2
        target=Fraction(k,64)
        phase=(a if _circular_fraction_distance(a,target)
               <=_circular_fraction_distance(b,target) else b)
    assert 0<=phase<1
    return phase


def recover_order_from_exact_phase(phase:Fraction,modulus:int,base:int):
    """Public modular check; no private factors or hidden eigenphase."""
    if (not isinstance(phase,Fraction) or not 0<=phase<1 or
        type(modulus) is not int or modulus<3 or type(base) is not int or
        not 1<base<modulus or gcd(base,modulus)!=1):
        raise ValueError("invalid public phase/order input")
    frac=phase.limit_denominator(modulus)
    d=frac.denominator
    return d if d>1 and pow(base,d,modulus)==1 else None
