"""Exact rational polynomial-signal obstruction for Attack 008.

These are standard Markov/Grover bounds against specified scalar processing
grammars. They do not lower-bound arbitrary classical or quantum algorithms.
"""
from dataclasses import dataclass
from fractions import Fraction
from math import isqrt


def grover_probability(p: Fraction, iterations: int) -> Fraction:
    """Exact sin^2((2k+1)asin(sqrt(p))) via Chebyshev recurrence."""
    if not isinstance(p, Fraction) or not 0 <= p <= 1:
        raise ValueError("p must be an exact probability in [0,1]")
    if type(iterations) is not int or iterations < 0:
        raise ValueError("iterations must be a nonnegative integer")
    m = 2 * iterations + 1
    x = 1 - 2 * p
    t0, t1 = Fraction(1), x
    for _ in range(1, m):
        t0, t1 = t1, 2*x*t1-t0
    out = (1-t1)/2
    if not 0 <= out <= 1:
        raise AssertionError("Chebyshev probability escaped [0,1]")
    return out


def required_grover_iterations_by_quadratic_bound(
    n: int, work_bits: int, threshold: Fraction = Fraction(2,3)
) -> int:
    """Smallest k compatible with (2k+1)^2*p >= threshold.

    Necessary, NOT sufficient for actual amplitude amplification.
    """
    if type(n) is not int or n < 1 or type(work_bits) is not int or work_bits < 0:
        raise ValueError("n>=1 and work_bits>=0 required")
    if not isinstance(threshold, Fraction) or not 0 < threshold <= 1:
        raise ValueError("threshold must be an exact rational in (0,1]")
    lhs = threshold.numerator * (1 << (2*(n+work_bits)))
    rhs = threshold.denominator
    d = isqrt((lhs + rhs - 1)//rhs)
    while rhs*d*d < lhs:
        d += 1
    while d > 0 and rhs*(d-1)*(d-1) >= lhs:
        d -= 1
    if d%2 == 0:
        d += 1
    return (d-1)//2


def required_polynomial_degree_by_markov(
    n: int, work_bits: int, gap: Fraction = Fraction(1,3)
) -> int:
    """Bounded polynomial G:[0,1]->[0,1], G(p*)-G(0)>=gap.

    The Markov bound |G'|<=2d^2 gives 2d^2*p*>=gap.
    """
    if type(n) is not int or n < 1 or type(work_bits) is not int or work_bits < 0:
        raise ValueError("n>=1 and work_bits>=0 required")
    if not isinstance(gap, Fraction) or not 0 < gap <= 1:
        raise ValueError("gap must be an exact rational in (0,1]")
    lhs = gap.numerator*(1 << (2*(n+work_bits)))
    rhs = 2*gap.denominator
    d = isqrt((lhs + rhs-1)//rhs)
    while rhs*d*d < lhs:
        d += 1
    while d > 0 and rhs*(d-1)*(d-1) >= lhs:
        d -= 1
    return d


@dataclass(frozen=True)
class GapBarrier:
    n_inputs: int
    work_bits: int
    raw_unique_sat_probability: Fraction
    markov_polynomial_min_degree: int
    grover_min_iterations_by_bound: int
    full_public_input: bool
    unrestricted_lower_bound_proved: bool


def certify_unique_sat_barrier(n: int, work_bits: int) -> GapBarrier:
    if type(n) is not int or n < 1 or type(work_bits) is not int or work_bits < 0:
        raise ValueError("invalid dimensions")
    return GapBarrier(
        n, work_bits, Fraction(1, 1 << (2*(n+work_bits))),
        required_polynomial_degree_by_markov(n, work_bits),
        required_grover_iterations_by_quadratic_bound(n, work_bits),
        True, False
    )


def toy_hccz_interference_circuits():
    """Five-wire public 1/4-versus-3/4 controls, both trivially classical."""
    from .hccz_circuit import Gate
    no = (Gate("H",(0,)),Gate("H",(1,)),Gate("H",(2,)),
          Gate("CCZ",(0,1,2)),Gate("H",(0,)))
    yes = no + (Gate("H",(0,)),Gate("CCZ",(0,3,4)),Gate("H",(0,)))
    return {"n_wires":5, "basis":(1<<3)|(1<<4), "no":no, "yes":yes}
