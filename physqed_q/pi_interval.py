"""Exact rational pi brackets from the Machin arctangent identity.

pi = 16 atan(1/5) - 4 atan(1/239).
For x in (0,1), atan(x) is an alternating, decreasing series.
Its first N terms plus the first omitted signed term give rigorous
lower/upper rational brackets. This module uses only Fraction, no
floating point, no stored decimal value of pi, and no external CAS.

The result is classical mathematical prior art. Its role is to
certify QASM decimal-radian -> rational-pi conversion without guessing
a floating-point pi.
"""
from fractions import Fraction

N_TERMS=24
MAX_PI_DEN=1000000000000


def atan_bracket(x,n=N_TERMS):
    if (type(x) is not Fraction or not 0<x<1 or
        type(n) is not int or not 2<=n<=40):
        raise ValueError("bounded positive rational arctangent only")
    total=sum(((-1)**k*x**(2*k+1)/Fraction(2*k+1)
               for k in range(n)),Fraction(0))
    tail=x**(2*n+1)/Fraction(2*n+1)
    if n%2==0:
        return total,total+tail
    return total-tail,total


def pi_bracket():
    alo,ahi=atan_bracket(Fraction(1,5))
    blo,bhi=atan_bracket(Fraction(1,239))
    lower=16*alo-4*bhi
    upper=16*ahi-4*blo
    if not Fraction(3)<lower<upper<Fraction(22,7):
        raise ArithmeticError("Machin rational pi bounds invalid")
    return lower,upper


PI_LOWER,PI_UPPER=pi_bracket()


def approximate_decimal_radians_as_pi(theta):
    """Return (q, eps) s.t. |theta - pi*q| <= eps exactly rational.

    theta is the literal decimal interpreted as exact rational radians.
    q is bounded to denominator<=10**12. With pi in [L,U] and q
    chosen by closest small rational to theta/pi midpoint, the maximum
    of endpoint distances gives an EXACT rational certificate.
    """
    if type(theta) is not Fraction or abs(theta)>100:
        raise ValueError("unbounded or nonexact decimal-radian input")
    midpoint=(PI_LOWER+PI_UPPER)/2
    q=(theta/midpoint).limit_denominator(MAX_PI_DEN)
    if abs(q)>32:
        raise ValueError("angle outside vNext rational-pi scope")
    epsilon=max(abs(theta-q*PI_LOWER),
                abs(theta-q*PI_UPPER))
    # Rigorous; no floating point comparisons.
    if epsilon<0:
        raise ArithmeticError("impossible signed approximation bound")
    return q,epsilon
