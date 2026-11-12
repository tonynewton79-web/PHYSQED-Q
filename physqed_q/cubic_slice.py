"""Exact Forrelation for cubic phases with a supplied low linear-quadratic factor rank.

Classical polynomial-time shortcut for O(log n) factors; no class separation.
"""
from dataclasses import dataclass
from fractions import Fraction


def _check_monomials(n, terms, degree):
    if not isinstance(terms, tuple) or len(terms) != len(set(terms)):
        raise ValueError('monomial list must be an unambiguous tuple')
    if any(type(a) is not int or a < 0 or a >= 1 << n or a.bit_count() > degree
           for a in terms):
        raise ValueError('invalid ANF monomial')


def _xor(s, t):
    if t in s:
        s.remove(t)
    else:
        s.add(t)


@dataclass(frozen=True)
class Phase:
    n: int
    quadratic: tuple[int, ...] = ()
    factors: tuple[tuple[int, tuple[int, ...]], ...] = ()

    def __post_init__(self):
        if type(self.n) is not int or self.n < 1:
            raise ValueError('n must be positive')
        _check_monomials(self.n, self.quadratic, 2)
        if not isinstance(self.factors, tuple):
            raise ValueError('factors must be a tuple')
        for ell, q in self.factors:
            if type(ell) is not int or ell <= 0 or ell >= 1 << self.n:
                raise ValueError('factor must have nonzero linear mask')
            _check_monomials(self.n, q, 2)

    def evaluate(self, x):
        if type(x) is not int or x < 0 or x >= 1 << self.n:
            raise ValueError('invalid input')
        val = sum((x & t) == t for t in self.quadratic) & 1
        for ell, q in self.factors:
            val ^= ((x & ell).bit_count() & 1) & (sum((x & t) == t for t in q) & 1)
        return val

    def expanded_anf(self):
        terms = set(self.quadratic)
        for ell, q in self.factors:
            for j in range(self.n):
                if ell & (1 << j):
                    for t in q:
                        _xor(terms, t | (1 << j))
        return tuple(sorted(terms))


def complete_cubic(n):
    """e3(x) = e1(x)*e2(x), exactly in the Boolean ring F2[x]/(x_i^2-x_i)."""
    if type(n) is not int or n < 3:
        raise ValueError('requires n >= 3')
    return Phase(n, factors=(((1 << n) - 1,
                tuple((1 << i) | (1 << j) for i in range(n)
                      for j in range(i + 1, n))),))


def quadratic_sign_sum(n, terms):
    """Integer sum_z (-1)^Q(z), using exact paired elimination."""
    _check_monomials(n, tuple(terms), 2)
    mon = set(terms)
    active = (1 << n) - 1
    pivots = 0
    while True:
        edge = next((t for t in mon if t.bit_count() == 2), None)
        if edge is None:
            break
        a = edge & -edge
        b = edge ^ a
        nxt = set()
        L = set()
        R = set()
        for t in mon:
            if t == edge:
                continue
            if t & a:
                _xor(L, t ^ a)
            elif t & b:
                _xor(R, t ^ b)
            else:
                nxt.add(t)
        for l in L:
            for r in R:
                _xor(nxt, l | r)
        mon = nxt
        active ^= a | b
        pivots += 1
    if any(t != 0 for t in mon):
        return 0
    return (-1 if 0 in mon else 1) << (pivots + active.bit_count())


@dataclass(frozen=True)
class Result:
    n: int
    factor_count: int
    gaussian_branches: int
    signed_sum: int
    probability: Fraction


def exact_forrelation(p: Phase, q: Phase, *, max_factors=8):
    """Computes S=sum_xy (-1)^(p(x)+x.y+q(y)) via <=4**r Gauss sums.

    A supplied degree-3 factorization is part of the explicit input, not an
    inferred promise about factorization or generic random cubic instances.
    """
    if not isinstance(p, Phase) or not isinstance(q, Phase) or p.n != q.n:
        raise ValueError('equal-size Phase inputs required')
    n = p.n
    r = len(p.factors) + len(q.factors)
    if type(max_factors) is not int or max_factors < 0 or r > max_factors:
        raise ValueError('factor rank exceeds fixed budget')
    base = set()
    for t in p.quadratic:
        _xor(base, t)
    for t in q.quadratic:
        _xor(base, t << n)
    for i in range(n):
        _xor(base, (1 << i) | (1 << (n + i)))
    factors = list(p.factors) + [(ell << n, tuple(t << n for t in quad))
                                 for ell, quad in q.factors]
    total = 0
    for a in range(1 << r):
        for b in range(1 << r):
            mono = set(base)
            if ((a & b).bit_count() & 1):
                _xor(mono, 0)
            for j, (ell, quad) in enumerate(factors):
                if (a >> j) & 1:
                    for t in quad:
                        _xor(mono, t)
                if (b >> j) & 1:
                    for i in range(2 * n):
                        if ell & (1 << i):
                            _xor(mono, 1 << i)
            total += quadratic_sign_sum(2 * n, tuple(mono))
    if total % (1 << r):
        raise AssertionError('invalid Fourier-selector divisibility')
    S = total >> r
    return Result(n, r, 4 ** r, S, Fraction(S * S, 1 << (3 * n)))


def independent_walsh(p: Phase, q: Phase):
    if p.n != q.n or p.n > 16:
        raise ValueError('small equal-size inputs only')
    n = p.n
    N = 1 << n
    data = [1 - 2 * p.evaluate(x) for x in range(N)]
    for bit in range(n):
        h = 1 << bit
        for j in range(0, N, 2 * h):
            for k in range(j, j + h):
                a, b = data[k], data[k + h]
                data[k], data[k + h] = a + b, a - b
    return sum((1 - 2 * q.evaluate(y)) * data[y] for y in range(N))
