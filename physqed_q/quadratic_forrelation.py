"""Exact explicit quadratic-phase Forrelation by polynomial-time Gauss sums.

Research-only. All results are classical and exact, not a BPP/BQP separation.
"""
from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class QuadraticPhase:
    """ANF: constant XOR parity(linear & x) XOR XOR_(i,j in pairs) x_i*x_j."""
    n: int
    pairs: tuple[tuple[int, int], ...] = ()
    linear: int = 0
    constant: int = 0

    def __post_init__(self):
        if type(self.n) is not int or self.n < 1:
            raise ValueError("n must be a positive integer")
        if type(self.linear) is not int or not (0 <= self.linear < (1 << self.n)):
            raise ValueError("linear must be an n-bit nonnegative mask")
        if type(self.constant) is not int or self.constant not in (0, 1):
            raise ValueError("constant must be 0 or 1")
        if not isinstance(self.pairs, tuple):
            raise ValueError("pairs must be a tuple")
        if any(not isinstance(edge, tuple) or len(edge) != 2 or
               any(type(v) is not int for v in edge) or
               not (0 <= edge[0] < edge[1] < self.n)
               for edge in self.pairs):
            raise ValueError("each pair must be (i,j), 0 <= i < j < n")
        if len(set(self.pairs)) != len(self.pairs):
            raise ValueError("pairs must not contain duplicates")

    def evaluate(self, x: int) -> int:
        if type(x) is not int or not (0 <= x < (1 << self.n)):
            raise ValueError("x out of range")
        value = self.constant ^ ((x & self.linear).bit_count() & 1)
        for i, j in self.pairs:
            value ^= ((x >> i) & 1) & ((x >> j) & 1)
        return value


def _toggle(monomials: set[int], mask: int) -> None:
    if mask in monomials:
        monomials.remove(mask)
    else:
        monomials.add(mask)


def _sum_quadratic_sign(m: int, monomials: set[int]) -> tuple[int, int, int]:
    """Return (sign, power, radical_dim); sum is sign*2**power or zero.

    Exact elimination uses sum_ab (-1)^(ab+aL+bM+R)=2*(-1)^(LM+R).
    """
    if type(m) is not int or m < 0:
        raise ValueError("invalid number of variables")
    mon = set(monomials)
    if any(type(mask) is not int or mask < 0 or mask >= (1 << m)
           or mask.bit_count() > 2 for mask in mon):
        raise ValueError("monomials must have degree at most 2 in m variables")
    active = (1 << m) - 1
    pivots = 0
    while True:
        edge = next((term for term in mon if term.bit_count() == 2), None)
        if edge is None:
            break
        i_mask = edge & -edge
        j_mask = edge ^ i_mask
        pair = i_mask | j_mask
        rest = active ^ pair
        L = set()
        M = set()
        R = set()
        for term in mon:
            if term == pair:
                continue
            if term & i_mask:
                _toggle(L, term ^ i_mask)
            elif term & j_mask:
                _toggle(M, term ^ j_mask)
            else:
                R.add(term)
        for a in L:
            for b in M:
                _toggle(R, a | b)
        if any(term & pair for term in R):
            raise AssertionError("elimination retained a pivot variable")
        mon = R
        active = rest
        pivots += 1
    radical_dim = active.bit_count()
    if any(term != 0 for term in mon):
        return (0, 0, radical_dim)
    return ((-1 if 0 in mon else 1), pivots + radical_dim, radical_dim)


@dataclass(frozen=True)
class ForrelationResult:
    n: int
    signed_sum: int
    radical_dimension: int
    squared_amplitude: Fraction

    @property
    def sign(self) -> int:
        return (self.signed_sum > 0) - (self.signed_sum < 0)

    @property
    def amplitude_expression(self) -> str:
        if self.signed_sum == 0:
            return "0"
        prefix = "-" if self.signed_sum < 0 else "+"
        return f"{prefix}2^(({self.radical_dimension}-{self.n})/2)"


def exact_forrelation(f: QuadraticPhase, g: QuadraticPhase) -> ForrelationResult:
    """No truth tables; classical polynomial time in explicit O(n^2) ANF."""
    if f.n != g.n:
        raise ValueError("f and g must have the same bit count")
    n = f.n
    mon = set()
    if f.constant ^ g.constant:
        mon.add(0)
    for i in range(n):
        if (f.linear >> i) & 1:
            mon.add(1 << i)
        if (g.linear >> i) & 1:
            mon.add(1 << (n+i))
        mon.add((1 << i) | (1 << (n+i)))
    for i,j in f.pairs:
        mon.add((1 << i) | (1 << j))
    for i,j in g.pairs:
        mon.add((1 << (n+i)) | (1 << (n+j)))
    sign, exponent, k = _sum_quadratic_sign(2*n, mon)
    signed_sum = sign * (1 << exponent) if sign else 0
    squared = Fraction(signed_sum * signed_sum, 1 << (3*n))
    if signed_sum and squared != Fraction(1 << k, 1 << n):
        raise AssertionError("Gauss sum / radical dimension inconsistency")
    return ForrelationResult(n, signed_sum, k, squared)


def independent_walsh_sum(f: QuadraticPhase, g: QuadraticPhase) -> int:
    """Independent O(n*2^n) reference via integer Walsh transform."""
    if f.n != g.n:
        raise ValueError("bit-count mismatch")
    n = f.n
    N = 1 << n
    data = [1 - 2*f.evaluate(x) for x in range(N)]
    for bit in range(n):
        step = 1 << bit
        for offset in range(0, N, 2*step):
            for i in range(offset, offset+step):
                a, b = data[i], data[i+step]
                data[i], data[i+step] = a+b, a-b
    return sum((1 - 2*g.evaluate(y))*data[y] for y in range(N))
