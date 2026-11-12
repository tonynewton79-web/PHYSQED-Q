"""Attack 004: dense cubic bent-dual phase pairs and exact auditing.

This is a classical shortcut for an explicit high-treewidth perfect-gap
Forrelation family, NOT a BPP/BQP separation or new bent construction.
"""
from dataclasses import dataclass
from fractions import Fraction
from .cubic_bandwidth import CubicPhase


def quadratic_controls(r: int) -> tuple[tuple[tuple[int, int], ...], ...]:
    if type(r) is not int or r < 2:
        raise ValueError("r must be an integer >= 2")
    return tuple(tuple((i,k) for i in range(r) for k in range(i+1,r)
                       if j%2==0 or (i+2*k+3*j)%5<4)
                 for j in range(r))


def quadratic_vector(r: int, a: int) -> int:
    if type(a) is not int or not 0 <= a < (1<<r):
        raise ValueError("a must be r-bit integer")
    value=0
    for j, edges in enumerate(quadratic_controls(r)):
        parity=0
        for i,k in edges:
            parity^=((a>>i)&1)&((a>>k)&1)
        value|=parity<<j
    return value


def pi_involution(r: int, y: int) -> int:
    """pi(a,b) = (a,b XOR Q(a)) = pi_inverse(a,b)."""
    if type(y) is not int or not 0 <= y < (1 << (2*r)):
        raise ValueError("y must be 2r-bit integer")
    mask=(1<<r)-1
    a,b=y&mask,y>>r
    return a|((b^quadratic_vector(r,a))<<r)


def make_pair(r: int, *, tilt: int=0, sign_flip: bool=False) -> tuple[CubicPhase,CubicPhase]:
    """n=4r; p(x,y)=x.pi(y); g(u,v)=v.pi(u)+tilt.(u,v)+flip."""
    control=quadratic_controls(r)
    n=4*r
    if type(tilt) is not int or not 0 <= tilt < (1<<n):
        raise ValueError("tilt must be an n-bit mask")
    quadratic=[(1<<i)|(1<<(2*r+i)) for i in range(r)]
    quadratic += [(1<<(r+j))|(1<<(3*r+j)) for j in range(r)]
    p_terms=list(quadratic)
    g_terms=list(quadratic)
    for j, edges in enumerate(control):
        for i,k in edges:
            p_terms.append((1<<(r+j))|(1<<(2*r+i))|(1<<(2*r+k)))
            g_terms.append((1<<(3*r+j))|(1<<i)|(1<<k))
    for i in range(n):
        if tilt&(1<<i):
            g_terms.append(1<<i)
    if sign_flip:
        g_terms.append(0)
    return CubicPhase(n,tuple(p_terms)),CubicPhase(n,tuple(g_terms))


def direct_p(r: int, z: int) -> int:
    m=2*r
    if type(z) is not int or not 0 <= z < (1<<(2*m)):
        raise ValueError("z out of range")
    x,y=z&((1<<m)-1),z>>m
    return (x&pi_involution(r,y)).bit_count()&1


def direct_g(r: int, z: int, tilt: int=0, sign_flip: bool=False) -> int:
    m=2*r
    if type(z) is not int or not 0 <= z < (1<<(2*m)):
        raise ValueError("z out of range")
    u,v=z&((1<<m)-1),z>>m
    return ((v&pi_involution(r,u)).bit_count() ^ (z&tilt).bit_count()
            ^ int(sign_flip))&1


@dataclass(frozen=True)
class ExactPairCertificate:
    r: int
    n: int
    cubic_terms_per_phase: int
    primal_clique_size: int
    treewidth_lower_bound: int
    all_order_bandwidth_lower_bound: int
    classically_decidable: bool
    decision: str
    signed_forrelation: int
    quantum_zero_probability: Fraction


def classify_explicit_pair(r: int,p: CubicPhase,g: CubicPhase) -> ExactPairCertificate:
    """Deterministic polynomial-time decision; refuse outside the promise."""
    if not isinstance(p,CubicPhase) or not isinstance(g,CubicPhase):
        raise TypeError("p and g must be CubicPhase objects")
    expected_p,dual=make_pair(r)
    n=4*r
    cubic_count=sum(m.bit_count()==3 for m in expected_p.monomials)
    decision="OUTSIDE_PROMISE"
    sign=0
    probability=Fraction(0)
    if p.n==n and g.n==n and set(p.monomials)==set(expected_p.monomials):
        delta=set(g.monomials)^set(dual.monomials)
        if all(m.bit_count()<=1 for m in delta):
            tilted=any(m!=0 for m in delta)
            decision="NO" if tilted else "YES"
            sign=0 if tilted else (-1 if 0 in delta else 1)
            probability=Fraction(0 if tilted else 1)
    return ExactPairCertificate(r,n,cubic_count,r,r-1,r,True,decision,sign,probability)


def _walsh(vector: list[int]) -> list[int]:
    size=len(vector)
    if size<1 or size&(size-1):
        raise ValueError("vector length must be power of two")
    a=vector[:]
    half=1
    while half<size:
        for start in range(0,size,2*half):
            for i in range(start,start+half):
                x,y=a[i],a[i+half]
                a[i],a[i+half]=x+y,x-y
        half*=2
    return a


def all_linear_tilt_numerators(p:CubicPhase,g:CubicPhase,max_n:int=12)->list[int]:
    """Exponential independent verification only, not a scalable algorithm."""
    if p.n!=g.n or p.n>max_n or p.n<1:
        raise ValueError("unsupported dimension for independent full-mask audit")
    N=1<<p.n
    fhat=_walsh([1-2*p.evaluate(x) for x in range(N)])
    return _walsh([fhat[y]*(1-2*g.evaluate(y)) for y in range(N)])


def verify_mask_parseval(p:CubicPhase,g:CubicPhase,max_n:int=12)->bool:
    values=all_linear_tilt_numerators(p,g,max_n)
    return sum(s*s for s in values)==(1<<(3*p.n))


def three_query_classical_tilt_test(r:int,query_g,y1:int,y2:int)->str:
    """3 Boolean queries: yes succeeds 1, every nonzero tilt succeeds 3/4.

    This success guarantee assumes independent uniform n-bit sample points.
    """
    quadratic_controls(r)
    N=1<<(4*r)
    if any(type(y) is not int or not (0<=y<N) for y in (y1,y2)):
        raise ValueError("samples must be n-bit integers")
    if not callable(query_g):
        raise TypeError("query_g must be callable")
    vals=[query_g(y) for y in (0,y1,y2)]
    if any(type(v) is not int or v not in (0,1) for v in vals):
        raise ValueError("Boolean oracle must return 0 or 1")
    baseline=vals[0]^direct_g(r,0)
    differences=[vals[j+1]^direct_g(r,y)^baseline
                 for j,y in enumerate((y1,y2))]
    return "NO" if any(differences) else "YES"


def public_dual_sample_mean(r:int,query_g,sample_points:tuple[int,...])->Fraction:
    """Unbiased classical sample mean of signed Forrelation for public bent dual.

    Any polynomial-time evaluable second phase q is allowed, not only tilts.
    """
    quadratic_controls(r)
    n=4*r
    if not isinstance(sample_points,tuple) or not sample_points:
        raise ValueError("sample_points must be nonempty tuple")
    if not callable(query_g):
        raise TypeError("query_g must be callable")
    total=0
    for y in sample_points:
        if type(y) is not int or not 0<=y<(1<<n):
            raise ValueError("sample point out of n-bit range")
        output=query_g(y)
        if type(output) is not int or output not in (0,1):
            raise ValueError("oracle output must be Boolean")
        total+=1-2*(output^direct_g(r,y))
    return Fraction(total,len(sample_points))
