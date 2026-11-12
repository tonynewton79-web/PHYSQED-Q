"""Exact signed Forrelation of explicit bounded-bandwidth cubic Boolean phases.

Constructive classical shortcut, not a BPP/BQP separation. All arithmetic
is exact: integer transfer-state contraction and rational probabilities.
"""
from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class CubicPhase:
    """Boolean ANF as XOR of squarefree monomial bitmasks (degree <= 3).

    Monomial 0 is the constant 1; the phase value is (-1)^evaluate(x).
    """
    n: int
    monomials: tuple[int, ...] = ()

    def __post_init__(self):
        if type(self.n) is not int or self.n < 1:
            raise ValueError("n must be a positive integer")
        if not isinstance(self.monomials, tuple):
            raise ValueError("monomials must be a tuple")
        if len(set(self.monomials)) != len(self.monomials):
            raise ValueError("ANF monomials must be unique")
        if any(type(mask) is not int or not (0 <= mask < (1 << self.n))
               or mask.bit_count() > 3 for mask in self.monomials):
            raise ValueError("invalid degree <=3 ANF bitmask")

    def evaluate(self, x: int) -> int:
        if type(x) is not int or not (0 <= x < (1 << self.n)):
            raise ValueError("x is not an n-bit integer")
        return sum((x & mask) == mask for mask in self.monomials) & 1

    def bandwidth(self) -> int:
        return max((mask.bit_length() - ((mask & -mask).bit_length() - 1)
                    for mask in self.monomials if mask), default=1)


@dataclass(frozen=True)
class CubicForrelationResult:
    n: int
    bandwidth: int
    signed_sum: int
    squared_amplitude: Fraction
    max_active_states: int

    @property
    def amplitude_expression(self) -> str:
        return f"({self.signed_sum}) / 2^(3*{self.n}/2)"


def relabel_phase(phase: CubicPhase, order: tuple[int, ...]) -> CubicPhase:
    """Relabel a phase by original variable indices in new left-to-right order."""
    n = phase.n
    if (not isinstance(order, tuple) or len(order) != n
            or any(type(j) is not int for j in order)
            or set(order) != set(range(n))):
        raise ValueError("order must be a permutation tuple of range(n)")
    pos = [0]*n
    for new, old in enumerate(order):
        pos[old] = new
    terms = []
    for m in phase.monomials:
        mapped = 0
        for i in range(n):
            if m & (1 << i):
                mapped |= 1 << pos[i]
        terms.append(mapped)
    return CubicPhase(n, tuple(terms))


def exact_banded_forrelation(f: CubicPhase, g: CubicPhase,
                             *, max_bandwidth: int = 10,
                             order: tuple[int, ...] | None = None) -> CubicForrelationResult:
    """Compute S=sum_(x,y) (-1)^[f(x)+x.y+g(y)] without truth tables.

    In the specified common variable order, let w be the largest monomial
    span. Uses O(n*4**w*poly(input_size)) arithmetic and at most 4**(w-1)
    integer states. An explicitly supplied order simultaneously relabels
    both phases, preserving the Fourier inner product.
    """
    if not isinstance(f, CubicPhase) or not isinstance(g, CubicPhase):
        raise TypeError("f and g must be CubicPhase objects")
    if f.n != g.n:
        raise ValueError("phase dimensions differ")
    if type(max_bandwidth) is not int or max_bandwidth < 1:
        raise ValueError("max_bandwidth must be a positive integer")
    n = f.n
    if order is not None:
        f = relabel_phase(f, order)
        g = relabel_phase(g, order)
    w = max(f.bandwidth(), g.bandwidth())
    if w > max_bandwidth:
        raise ValueError(f"bandwidth {w} exceeds certified budget {max_bandwidth}")
    stage = [[] for _ in range(n)]
    constant = 0
    for side, phase in enumerate((f,g)):
        for mask in phase.monomials:
            if mask == 0:
                constant ^= 1
                continue
            end = mask.bit_length()-1
            needed = 0
            for j in range(end+1):
                if mask & (1 << j):
                    needed |= 1 << (2*(end-j)+side)
            stage[end].append(needed)
    state_mask = (1 << (2*(w-1))) - 1
    states = {0:1}
    max_states = 1
    for i in range(n):
        updated = {}
        for prev, weight in states.items():
            for xy in range(4):
                window = (prev << 2) | xy
                parity = (xy == 3)
                for needed in stage[i]:
                    parity ^= ((window & needed) == needed)
                new_key = window & state_mask
                updated[new_key] = updated.get(new_key,0) + (-weight if parity else weight)
        states = updated
        max_states = max(max_states,len(states))
    S = sum(states.values())
    if constant:
        S = -S
    return CubicForrelationResult(n,w,S,Fraction(S*S,1 << (3*n)),max_states)


def independent_walsh_sum(f: CubicPhase, g: CubicPhase) -> int:
    """Independent O(n*2**n) integer Walsh check for n <= 16."""
    if f.n != g.n:
        raise ValueError("phase dimensions differ")
    n = f.n
    if n > 16:
        raise ValueError("independent Walsh oracle is limited to n <= 16")
    size = 1 << n
    entries = [1-2*f.evaluate(x) for x in range(size)]
    for i in range(n):
        half = 1 << i
        for start in range(0,size,2*half):
            for j in range(start,start+half):
                a,b = entries[j],entries[j+half]
                entries[j],entries[j+half] = a+b,a-b
    return sum((1-2*g.evaluate(y))*entries[y] for y in range(size))


def consecutive_cubic_chain(n: int) -> CubicPhase:
    """p(x) = XOR_{i=0}^{n-3} x_i*x_(i+1)*x_(i+2)."""
    if type(n) is not int or n < 3:
        raise ValueError("n must be at least 3")
    return CubicPhase(n,tuple(7 << i for i in range(n-2)))


def recover_cubic_chain_order(phase: CubicPhase) -> tuple[int, ...]:
    """Recognize a complete consecutive-triple cubic hypergraph.

    Reject any other hypergraph; validate the recovered order explicitly.
    Other terms still require a separate bandwidth check.
    """
    n = phase.n
    if n < 3:
        raise ValueError("three-variable cubic chain required")
    edges = [m for m in phase.monomials if m.bit_count()==3]
    if len(edges)!=n-2:
        raise ValueError("cubic support must contain exactly n-2 triples")
    covered = 0
    for edge in edges:
        covered |= edge
    if len(set(edges))!=len(edges) or covered!=((1<<n)-1):
        raise ValueError("chain must cover exactly n vertices")
    if n==3:
        return (0,1,2)

    def unique_index(mask):
        if mask.bit_count()!=1:
            raise ValueError("not a unique variable in chain construction")
        return mask.bit_length()-1

    adj=[[] for _ in edges]
    for i in range(len(edges)):
        for j in range(i+1,len(edges)):
            if (edges[i]&edges[j]).bit_count()==2:
                adj[i].append(j)
                adj[j].append(i)
    endpoints=[i for i,near in enumerate(adj) if len(near)==1]
    if len(endpoints)!=2 or any(len(near) not in (1,2) for near in adj):
        raise ValueError("cubic-overlap graph is not a path")
    walk=[endpoints[0]]
    while len(walk)<len(edges):
        choices=[j for j in adj[walk[-1]] if j not in walk]
        if len(choices)!=1:
            raise ValueError("cubic overlap graph has an ambiguous continuation")
        walk.append(choices[0])
    e=[edges[i] for i in walk]
    if n==4:
        first=unique_index(e[0]&~e[1])
        last=unique_index(e[1]&~e[0])
        common=tuple(i for i in range(n) if (e[0]&e[1])&(1<<i))
        order=(first,)+common+(last,)
    else:
        first=unique_index(e[0]&~e[1])
        third=unique_index(e[0]&e[1]&e[2])
        second=unique_index(e[0]&~((1<<first)|(1<<third)))
        ordered=[first,second,third]
        for i in range(1,len(e)):
            ordered.append(unique_index(e[i]&~e[i-1]))
        order=tuple(ordered)
    if (len(order)!=n or len(set(order))!=n or
            any(e[i]!=((1<<order[i])|(1<<order[i+1])|(1<<order[i+2]))
                for i in range(n-2))):
        raise ValueError("overlap path is not a consecutive-cubic chain")
    return order
