"""Attack 011: polynomial-size clean reversible modular exponentiation in H+CCZ.

This is a Shor *arithmetic core* and special 2-power-period Walsh experiment,
not a full Shor circuit. It does NOT synthesize inverse QFT or prove BPP!=BQP.
All work wires are cleaned by compute-copy-uncompute. No truth-table synthesis.
"""
from dataclasses import dataclass
from math import gcd
from typing import Tuple


@dataclass(frozen=True)
class Gate:
    kind: str
    qubits: tuple[int, ...]


@dataclass(frozen=True)
class ModexpCore:
    modulus: int
    base: int
    exponent_bits: int
    data_bits: int
    n_wires: int
    initial_basis: int
    output_wires: tuple[int, ...]
    work_wires: tuple[int, ...]
    gate_count: int
    toffoli_count: int
    hadamard_count: int
    gates: tuple[Gate, ...]


class _Builder:
    """Boolean DAG with fresh clean targets, XOR and AND only."""
    def __init__(self, exp_bits: int, data_bits: int):
        self.exp_bits = exp_bits
        self.data_bits = data_bits
        self.one = exp_bits
        self.one_second = exp_bits + 1
        self.zero = exp_bits + 2
        self.output = tuple(range(exp_bits + 3, exp_bits + 3 + data_bits))
        self.next = exp_bits + 3 + data_bits
        self.operations = []

    def xor(self, a: int, b: int) -> int:
        if a == self.zero:
            return b
        if b == self.zero:
            return a
        if a == b:
            return self.zero
        dest = self.next
        self.next += 1
        self.operations.append(('XOR', a, b, dest))
        return dest

    def and_(self, a: int, b: int) -> int:
        if a == self.zero or b == self.zero:
            return self.zero
        if a == self.one:
            return b
        if b == self.one:
            return a
        if a == b:
            return a
        dest = self.next
        self.next += 1
        self.operations.append(('AND', a, b, dest))
        return dest

    def mux(self, cond, yes, no):
        return self.xor(no, self.and_(cond, self.xor(yes, no)))

    def add(self, a: tuple[int, ...], b: tuple[int, ...], carry=None):
        if len(a) != len(b):
            raise ValueError('addition widths mismatch')
        if carry is None:
            carry = self.zero
        bits = []
        for x, y in zip(a, b):
            t = self.xor(x, y)
            bits.append(self.xor(t, carry))
            carry = self.xor(self.and_(x, y), self.and_(t, carry))
        return tuple(bits), carry

    def add_constant(self, a: tuple[int, ...], constant: int):
        b = tuple(self.one if (constant >> i) & 1 else self.zero
                  for i in range(len(a)))
        return self.add(a,b)

    def mul_mod(self, a: tuple[int, ...], factor: int, modulus: int):
        s = len(a)
        acc = (self.zero,) * (2*s)
        for shift in range(s):
            if not (factor >> shift) & 1:
                continue
            row = (self.zero,) * shift + a + (self.zero,) * (s-shift)
            acc, _ = self.add(acc, row)
        rem = (self.zero,) * s
        width = s+1
        for inbit in reversed(acc):
            shifted = (inbit,) + rem
            if len(shifted)!=width:
                raise AssertionError('reduction remainder width invariant')
            diff, carry = self.add_constant(shifted, (1<<width)-modulus)
            rem = tuple(self.mux(carry,diff[i],shifted[i]) for i in range(s))
        return rem

    def network(self, modulus: int, base: int, exponent_bits: int):
        # Using repeated squaring to compute each public modular factor.
        cur = (self.one,) + (self.zero,)*(self.data_bits-1)
        for j in range(exponent_bits):
            c=pow(base,1<<j,modulus)
            mult=self.mul_mod(cur,c,modulus)
            cur=tuple(self.mux(j,mult[i],cur[i])
                      for i in range(self.data_bits))
        return cur

    def _cnot(self, control, target):
        if control == self.one:
            return Gate('TOFFOLI',(self.one,self.one_second,target))
        if control == self.one_second:
            return Gate('TOFFOLI',(self.one,self.one_second,target))
        if control == self.zero:
            return None
        return Gate('TOFFOLI',(control,self.one,target))

    def reversible_gates(self, final_bits):
        gates=[]
        for kind,a,b,out in self.operations:
            if kind=='XOR':
                for control in (a,b):
                    op=self._cnot(control,out)
                    if op:
                        gates.append(op)
            elif kind=='AND':
                if len({a,b,out})!=3:
                    raise AssertionError('AND gate target overlaps controls')
                gates.append(Gate('TOFFOLI',(a,b,out)))
            else:
                raise AssertionError('unknown gate')
        forward=tuple(gates)
        copies=[]
        for dest,src in zip(self.output,final_bits):
            op=self._cnot(src,dest)
            if op:
                copies.append(op)
        return forward+tuple(copies)+tuple(reversed(forward))


def compile_modexp_core(modulus: int, base: int, exponent_bits: int,
                        *, include_final_hadamards: bool = False) -> ModexpCore:
    """Generate a POLYNOMIAL-size H+CCZ circuit for modular exponentiation.

    Initial state has two fixed |1> ancillas, all other registers blank.
    H^m on exponent -> coherent modular exponentiation; optional H^m for
    special Z_2^m Walsh sampling (NOT the inverse QFT needed by Shor).

    Gate count O(m*s^3), wires O(m*s^3) with s=ceil(log2(N)).
    """
    if (type(modulus) is not int or modulus < 3 or
            type(base) is not int or not 1 < base < modulus or
            gcd(base,modulus)!=1 or type(exponent_bits) is not int or
            exponent_bits < 1):
        raise ValueError('require modulus>=3, invertible base, m>=1')
    s=modulus.bit_length()
    b=_Builder(exponent_bits,s)
    result=b.network(modulus,base,exponent_bits)
    reversible=b.reversible_gates(result)
    hadamards=tuple(Gate('H',(j,)) for j in range(exponent_bits))
    toffoli_gates=hadamards+reversible+(hadamards if include_final_hadamards else ())
    actual=[]
    for g in toffoli_gates:
        if g.kind=='H':
            actual.append(g)
        else:
            a,c,t=g.qubits
            actual.extend((Gate('H',(t,)),Gate('CCZ',(a,c,t)),Gate('H',(t,))))
    fixed_basis=(1<<b.one)|(1<<b.one_second)
    return ModexpCore(modulus,base,exponent_bits,s,b.next,fixed_basis,
                      b.output,tuple(range(exponent_bits+3+s,b.next)),
                      len(actual),sum(g.kind=='TOFFOLI' for g in toffoli_gates),
                      sum(g.kind=='H' for g in actual),tuple(actual))


def sparse_integer_state(core: ModexpCore, *, maximum_support: int=1<<16):
    """Independent exact amplitude numerators; intentionally finite resource gate.

    Dynamic dictionary avoids a 2^(number_of_work_wires) dense state vector.
    Do NOT use this as an efficient strong-simulation claim at large exponent m.
    """
    state={core.initial_basis:1}
    h=0
    for gate in core.gates:
        if gate.kind=='H':
            mask=1<<gate.qubits[0]
            new={}
            for bits,amp in state.items():
                a=bits&~mask
                b=bits|mask
                new[a]=new.get(a,0)+amp
                new[b]=new.get(b,0)+(-amp if bits&mask else amp)
            state={bits:amp for bits,amp in new.items() if amp}
            h+=1
        elif gate.kind=='CCZ':
            mask=sum(1<<j for j in gate.qubits)
            state={z: (-v if z&mask==mask else v) for z,v in state.items()}
        else:
            raise AssertionError('non H/CCZ gate escaped compiler')
        if len(state)>maximum_support:
            raise ValueError('sparse exact reference exceeded support limit')
    if sum(z*z for z in state.values())!=(1<<h):
        raise AssertionError('exact state normalization failure')
    return state,h


def decoded_modexp_state(core:ModexpCore,state:dict[int,int],h:int,
                         *, final_hadamards:bool=False):
    """Check clean ancillas and output; return exact marginal probabilities.

    Keys are (exponent_readout, modular_output) with exact integer numerator
    norm and denominator 2^h; an exponent post-H register is NOT x itself.
    """
    from fractions import Fraction
    m=core.exponent_bits
    xmask=(1<<m)-1
    outputmask=(1<<core.data_bits)-1
    fixed=core.initial_basis
    out={}
    for z,amp in state.items():
        x=z&xmask
        value=sum(((z>>idx)&1)<<j for j,idx in enumerate(core.output_wires))
        allowed=fixed|x|sum(((value>>j)&1)<<idx
                            for j,idx in enumerate(core.output_wires))
        if allowed!=z:
            raise AssertionError('compute-copy-uncompute did not clean work')
        out[(x,value)]=out.get((x,value),0)+amp*amp
        if not final_hadamards and value!=pow(core.base,x,core.modulus):
            raise AssertionError('modexp output mismatch')
    return {k:Fraction(v,1<<h) for k,v in out.items()}


def order_toy(a: int, N:int):
    """Brute-force reference ONLY. Never use in polynomial-time claim."""
    if type(N) is not int or N>10000 or N<3 or gcd(a,N)!=1:
        raise ValueError('small coprime reference only')
    z=1
    for k in range(1,N+1):
        z=(z*a)%N
        if z==1:return k
    raise AssertionError('no multiplicative order')


def exact_walsh_marginal(a:int,N:int,m:int):
    """Independent O(4^m) character sum, for small diagnostics only."""
    from fractions import Fraction
    if type(m) is not int or m<1 or m>9:
        raise ValueError('small exponent reference only')
    Y=[pow(a,x,N) for x in range(1<<m)]
    vals={}
    for z in range(1<<m):
        counts={}
        for x,y in enumerate(Y):
            counts[y]=counts.get(y,0)+(1 if (x&z).bit_count()%2==0 else -1)
        vals[z]=sum(k*k for k in counts.values())
    return {z:Fraction(v,1<<(2*m)) for z,v in vals.items()}
