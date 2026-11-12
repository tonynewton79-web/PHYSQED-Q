"""Finite exact H/CCZ/Toffoli circuit checker for the BQP-complete target.

Output probability computed as integer numerator / 2**(#Hadamards).
The universal-computing gate-set theorem is prior art, not proved here.
"""
from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class Gate:
    kind: str
    qubits: tuple[int, ...]


@dataclass(frozen=True)
class ExactCircuitResult:
    n: int
    basis: int
    hadamards: int
    state_numerators: tuple[int, ...]
    output_probability: Fraction


def _validate(n, gates, basis, output):
    if type(n) is not int or not 1 <= n <= 12:
        raise ValueError('bounded reference requires 1 <= n <= 12')
    if type(basis) is not int or not 0 <= basis < 1 << n:
        raise ValueError('invalid computational-basis input')
    if type(output) is not int or not 0 <= output < n:
        raise ValueError('invalid output qubit')
    if not isinstance(gates, (tuple, list)):
        raise ValueError('gates must be an ordered tuple/list')
    for gate in gates:
        if not isinstance(gate, Gate) or not isinstance(gate.qubits, tuple):
            raise ValueError('invalid gate')
        arity = {'H': 1, 'CCZ': 3, 'TOFFOLI': 3}.get(gate.kind)
        if arity is None or len(gate.qubits) != arity:
            raise ValueError('unknown gate or incorrect arity')
        if any(type(j) is not int or not 0 <= j < n for j in gate.qubits):
            raise ValueError('qubit index out of range')
        if len(set(gate.qubits)) != arity:
            raise ValueError('qubits must be distinct')


def compile_toffoli(gates):
    """Exact U_TOFFOLI = H_target CCZ_(control,control,target) H_target."""
    compiled = []
    for gate in gates:
        if not isinstance(gate, Gate):
            raise ValueError('invalid gate')
        if gate.kind == 'TOFFOLI':
            if len(gate.qubits) != 3 or len(set(gate.qubits)) != 3:
                raise ValueError('invalid Toffoli')
            a,b,c=gate.qubits
            compiled.extend((Gate('H',(c,)),Gate('CCZ',(a,b,c)),Gate('H',(c,))))
        elif gate.kind in ('H','CCZ'):
            compiled.append(gate)
        else:
            raise ValueError('unknown gate')
    return tuple(compiled)


def exact_run(n, gates, *, basis=0, output=0):
    """Exact dense bounded simulation, not a scalable classical solver."""
    _validate(n,gates,basis,output)
    state = [0]*(1<<n)
    state[basis]=1
    h=0
    for gate in gates:
        if gate.kind=='H':
            k=1<<gate.qubits[0]
            for group in range(0,len(state),2*k):
                for i in range(group,group+k):
                    a,b=state[i],state[i+k]
                    state[i],state[i+k]=a+b,a-b
            h+=1
        elif gate.kind=='CCZ':
            mask=sum(1<<j for j in gate.qubits)
            for z in range(len(state)):
                if (z&mask)==mask:
                    state[z]=-state[z]
        else:
            a,b,c=gate.qubits
            controls=(1<<a)|(1<<b)
            target=1<<c
            for z in range(len(state)):
                if (z&controls)==controls and not(z&target):
                    state[z],state[z|target]=state[z|target],state[z]
    if sum(z*z for z in state)!=(1<<h):
        raise AssertionError('integer amplitude normalization failure')
    prob = Fraction(sum(val*val for i,val in enumerate(state) if i&(1<<output)),1<<h)
    return ExactCircuitResult(n,basis,h,tuple(state),prob)
