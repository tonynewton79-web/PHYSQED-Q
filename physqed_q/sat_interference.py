"""Exact 3-CNF -> degree-three Boolean phase -> public H/CCZ reduction.

Established #P-hard strong-simulation paradigm, not BPP != BQP.
"""
from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class BoolGate:
    kind: str
    inputs: tuple[int, ...]
    output: int


@dataclass(frozen=True)
class Reduction:
    n_inputs: int
    clauses: tuple[tuple[int, ...], ...]
    gates: tuple[BoolGate, ...]
    output_wire: int
    work_bits: int
    constraint_bits: int
    phase_bits: int
    phase_monomials: tuple[int, ...]

    def phase(self, z: int) -> int:
        if type(z) is not int or not 0 <= z < (1 << self.phase_bits):
            raise ValueError("phase assignment out of range")
        return sum((z & mask) == mask for mask in self.phase_monomials) & 1

    @property
    def quantum_amplitude_denominator(self) -> int:
        return 1 << (self.n_inputs + self.work_bits)

    def predicted_probability(self, satisfying_count: int) -> Fraction:
        if type(satisfying_count) is not int or not (0 <= satisfying_count <= (1 << self.n_inputs)):
            raise ValueError("invalid satisfying count")
        return Fraction(satisfying_count ** 2, self.quantum_amplitude_denominator ** 2)


def _check_cnf(n, clauses):
    if type(n) is not int or n < 1:
        raise ValueError("n must be positive")
    if not isinstance(clauses, (tuple,list)) or not clauses:
        raise ValueError("nonempty clause sequence required")
    cleaned=[]
    for clause in clauses:
        if not isinstance(clause,(tuple,list)) or not 1 <= len(clause) <= 3:
            raise ValueError("clause size outside [1,3]")
        if any(type(l) is not int or l == 0 or abs(l) > n for l in clause):
            raise ValueError("invalid signed literal")
        cleaned.append(tuple(clause))
    return tuple(cleaned)


def sat_count(n, clauses):
    clauses=_check_cnf(n,clauses)
    return sum(
        all(any(bool((x >> (abs(lit)-1)) & 1) == (lit>0)
                for lit in clause) for clause in clauses)
        for x in range(1 << n)
    )


def compile_cnf(n: int, clauses) -> Reduction:
    """Uniform fresh-output fan-in-two Boolean-gate compiler."""
    clauses=_check_cnf(n,clauses)
    gates=[]
    next_wire=n
    neg_cache={}

    def gate(kind, inputs):
        nonlocal next_wire
        out=next_wire
        next_wire+=1
        gates.append(BoolGate(kind,tuple(inputs),out))
        return out

    def lit_wire(lit):
        j=abs(lit)-1
        if lit > 0:
            return j
        if j not in neg_cache:
            neg_cache[j]=gate("NOT",(j,))
        return neg_cache[j]

    clause_outputs=[]
    for clause in clauses:
        terms=[lit_wire(lit) for lit in clause]
        val=terms[0]
        for term in terms[1:]:
            val=gate("OR",(val,term))
        clause_outputs.append(val)
    output=clause_outputs[0]
    for term in clause_outputs[1:]:
        output=gate("AND",(output,term))

    w=len(gates)
    assert next_wire==n+w
    N=n+2*w+1
    terms=set()

    def toggle(mask):
        if mask in terms:
            terms.remove(mask)
        else:
            terms.add(mask)

    for j, g in enumerate(gates):
        multiplier=1 << (n+w+j)
        toggle(multiplier | (1 << g.output))
        if g.kind=="NOT":
            toggle(multiplier)
            toggle(multiplier | (1 << g.inputs[0]))
        elif g.kind in ("AND","OR"):
            a,b=(1 << i for i in g.inputs)
            toggle(multiplier | a | b)
            if g.kind=="OR":
                toggle(multiplier | a)
                toggle(multiplier | b)
        else:
            raise AssertionError("unsupported Boolean gate")

    last=1 << (n+2*w)
    toggle(last | (1 << output))
    toggle(last)    # enforce output=1
    if any(mask.bit_count()>3 for mask in terms):
        raise AssertionError("degree >3")
    return Reduction(n,clauses,tuple(gates),output,w,w+1,N,tuple(sorted(terms)))


def direct_phase_gap(reduction: Reduction, *, max_bits=17):
    """Exponential independent reference, deliberately size limited."""
    if reduction.phase_bits>max_bits:
        raise ValueError("direct signed reference exceeds finite size cap")
    return sum(1-2*reduction.phase(z) for z in range(1<<reduction.phase_bits))


def constraint_pairing_gap(reduction: Reduction):
    """Independent Boolean gate consistency check, no phase polynomial."""
    n,w=reduction.n_inputs,reduction.work_bits
    count=0
    for z in range(1<<(n+w)):
        valid=True
        for g in reduction.gates:
            inp=[(z>>i)&1 for i in g.inputs]
            if g.kind=="NOT": expected=inp[0]^1
            elif g.kind=="AND": expected=inp[0]&inp[1]
            elif g.kind=="OR": expected=inp[0]|inp[1]
            else: raise AssertionError("unknown gate")
            if ((z>>g.output)&1)!=expected:
                valid=False
                break
        if valid and ((z>>reduction.output_wire)&1):
            count+=1
    return count << reduction.constraint_bits


def hccz_program(reduction: Reduction):
    """(total_wires, basis_input, H/CCZ gates, global_sign).

    Two basis-|1> ancillas remain unchanged and are not Hadamarded.
    """
    N=reduction.phase_bits
    a,b=N,N+1
    gates=[("H",(j,)) for j in range(N)]
    sign=1
    for mask in reduction.phase_monomials:
        support=tuple(j for j in range(N) if (mask>>j)&1)
        if len(support)==0:
            sign=-sign
        elif len(support)==1:
            gates.append(("CCZ",(support[0],a,b)))
        elif len(support)==2:
            gates.append(("CCZ",support+(a,)))
        elif len(support)==3:
            gates.append(("CCZ",support))
        else:
            raise AssertionError("invalid degree")
    gates.extend(("H",(j,)) for j in range(N))
    return N+2,(1<<a)|(1<<b),tuple(gates),sign


def recover_count_from_probability(reduction: Reduction, probability: Fraction):
    """Exact integer square root, no floating point."""
    from math import isqrt
    if not isinstance(probability,Fraction) or not 0<=probability<=1:
        raise ValueError("invalid probability")
    z=probability*reduction.quantum_amplitude_denominator**2
    if z.denominator!=1:
        raise ValueError("probability outside exact count image")
    count=isqrt(z.numerator)
    if count*count!=z.numerator or count>(1<<reduction.n_inputs):
        raise ValueError("not an integer count square")
    return count


@dataclass(frozen=True)
class ApproximationCertificate:
    estimate: Fraction
    maximum_absolute_error: Fraction
    requested_error: Fraction
    method: str
    relevant_inputs: int
    enumerated_assignments: int


def additive_probability_approximation(reduction: Reduction, epsilon: Fraction):
    """Deterministic additive FPTAS for THIS restricted normalized family.

    P<=4^-w. If this is <=epsilon, output zero. Else enumerate <=w+1
    relevant input variables in the output cone, at most 2/sqrt(epsilon)
    assignments. No analogue is claimed for general H/CCZ circuits.
    """
    if not isinstance(reduction,Reduction):
        raise TypeError("reduction required")
    if not isinstance(epsilon,Fraction) or not (0<epsilon<=1):
        raise ValueError("epsilon must be rational and in (0,1]")
    w=reduction.work_bits
    bound=Fraction(1,1<<(2*w))
    if bound<=epsilon:
        return ApproximationCertificate(Fraction(0),bound,epsilon,"zero_bound",0,0)
    by_output={g.output:g for g in reduction.gates}
    pending=[reduction.output_wire]
    seen=set()
    leaves=set()
    while pending:
        k=pending.pop()
        if k in seen:
            continue
        seen.add(k)
        if k<reduction.n_inputs:
            leaves.add(k)
        else:
            pending.extend(by_output[k].inputs)
    relevant=tuple(sorted(leaves))
    if len(relevant)>w+1:
        raise AssertionError("fan-in 2 output-cone leaf bound failed")
    accepts=0
    for assignment in range(1<<len(relevant)):
        val={j:(assignment>>i)&1 for i,j in enumerate(relevant)}
        for g in reduction.gates:
            if g.output not in seen:
                continue
            inp=[val[j] for j in g.inputs]
            if g.kind=="NOT": val[g.output]=inp[0]^1
            elif g.kind=="AND": val[g.output]=inp[0]&inp[1]
            elif g.kind=="OR": val[g.output]=inp[0]|inp[1]
            else: raise AssertionError("unknown gate")
        accepts+=val[reduction.output_wire]
    fraction=Fraction(accepts,1<<len(relevant))
    exact=(fraction * Fraction(1,1<<w))**2
    return ApproximationCertificate(exact,Fraction(0),epsilon,"small_cone_exact",
                                    len(relevant),1<<len(relevant))
