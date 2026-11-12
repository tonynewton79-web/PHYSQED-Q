"""Uniform public-input H/CCZ MOD3 benchmark; no BPP/BQP separation.

The class lower bound against AC^0[2] is Razborov-Smolensky prior art.
This language has an O(n) classical algorithm.
"""
from dataclasses import dataclass
from .hccz_circuit import Gate, compile_toffoli


@dataclass(frozen=True)
class PublicMod3Certificate:
    input_size: int
    data_qubits: int
    total_qubits: int
    gates: tuple[Gate, ...]
    hadamards: int
    cczs: int
    description_independent_of_input: bool = True


def public_mod3_circuit(n: int) -> PublicMod3Certificate:
    """Fixed uniform gate sequence U_n, with public x supplied as input basis.

    Data: x_0,...,x_(n-1); work: a=n,b=n+1; fixed |1> ancillas:
    c=n+2,d=n+3. Starts with X_a, then for each x_i two Toffolis
    (x_i,a)->b and (x_i,b)->a, and finishes with X_b.
    All gates are compiled exactly to H and CCZ.
    """
    if type(n) is not int or n < 1:
        raise ValueError('n must be a positive integer')
    a,b,c,d=n,n+1,n+2,n+3
    def x_from_hccz(target):
        return (Gate('H',(target,)), Gate('CCZ',(target,c,d)),
                Gate('H',(target,)))
    ops=list(x_from_hccz(a))
    for i in range(n):
        ops.extend(compile_toffoli((Gate('TOFFOLI',(i,a,b)),
                                    Gate('TOFFOLI',(i,b,a)))))
    ops.extend(x_from_hccz(b))
    out=tuple(ops)
    h=sum(g.kind=='H' for g in out)
    z=sum(g.kind=='CCZ' for g in out)
    if len(out)!=6*n+6 or h!=4*n+4 or z!=2*n+2:
        raise AssertionError('gate-count regression')
    if any(g.kind not in ('H','CCZ') for g in out):
        raise AssertionError('escaped H/CCZ gate set')
    return PublicMod3Certificate(n,n,n+4,out,h,z)


def input_basis(n: int, x: int) -> int:
    if (type(n) is not int or n < 1 or type(x) is not int
            or not 0 <= x < (1<<n)):
        raise ValueError('input must be n-bit integer')
    return x | (1<<(n+2)) | (1<<(n+3))


def transition(a: int, b: int, control: int) -> tuple[int,int]:
    if (any(type(v) is not int for v in (a,b,control))
            or any(v not in (0,1) for v in (a,b,control))):
        raise ValueError('expected three Boolean bits')
    if control:
        b ^= a
        a ^= b
    return a,b


def streaming_mod3(n: int, x: int) -> int:
    """Explicit O(n) deterministic classical shortcut."""
    if (type(n) is not int or n < 1 or type(x) is not int
            or not 0 <= x < (1<<n)):
        raise ValueError('invalid public input')
    a,b=1,0
    for i in range(n):
        a,b=transition(a,b,(x>>i)&1)
    return 1^b


def prefix_residuals_witness(n: int, k: int = 2) -> tuple[tuple[int,...], ...]:
    """Sharp deterministic ordered-read-once branching-program width-3 gate."""
    if (type(n) is not int or type(k) is not int or n<4
            or not 2 <= k <= n-2):
        raise ValueError('need at least two bits on each side')
    prefixes=(0,1,3)
    suffixes=(0,1,3)
    mat=tuple(tuple(int((p.bit_count()+s.bit_count())%3==0)
                    for s in suffixes) for p in prefixes)
    if len(set(mat))!=3:
        raise AssertionError('lost distinct residuals')
    return mat


def uniform_description_query_ceiling(n: int) -> int:
    """Reading all O(n log n) public description bits needs O(n log n) queries.

    Says nothing about the cost of evaluating the described circuit.
    """
    if type(n) is not int or n < 1:
        raise ValueError('n must be positive')
    width=(n+4).bit_length()
    return (6*n+6)*(2+3*width)+n
