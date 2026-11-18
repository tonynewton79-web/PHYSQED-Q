"""Independent full 2^n native operator audit of PHYSQED-Q Mark II.

No fake backends, Qiskit, Aer, PyZX or network calls. This is an
independent dense *numeric* gate solver from the vNext matrix oracle,
not a formal proof of all numerical floating-point operations.
"""
from .vnext import VNextError
from .vnext_numeric import numeric_unitary,_evolve


def _dense(program):
    n=program["qubits"]
    ng=len(program["gates"])
    if n>4 or ng>4096:
        raise VNextError("Mark II dense audit exceeds bounded numerical scope")
    if ng<=512:
        return numeric_unitary(program,expanded_native=True)
    return [_evolve(program,j) for j in range(1<<n)]


def physical_operator_frobenius_error(receipt):
    """Reference = unrouted compiled unitary, then final SWAP permutation."""
    n=receipt["native_circuit"]["qubits"]
    initial=receipt["physical_initial_logical_layout"]
    logical=receipt["virtual_lowering_receipt"]["compiled"]["gates"]
    reference={"name":"unrouted-physical-reference","qubits":n,"gates":[
        {**{k:v for k,v in g.items() if k!="qubits"},
         "qubits":[initial[q] for q in g["qubits"]]}
        for g in logical]}
    ref=_dense(reference)
    routed=_dense(receipt["native_circuit"])
    perm=receipt["end_permutation_of_input_wire_states"]
    if sorted(perm)!=list(range(n)):
        raise VNextError("invalid physical-token final permutation")
    total=0.
    for a,b in zip(ref,routed):
        expected=[0j]*(1<<n)
        for basis_index,value in enumerate(a):
            output_index=sum(((basis_index>>wire)&1)<<position
                             for wire,position in enumerate(perm))
            expected[output_index]=value
        total+=sum(abs(x-y)**2 for x,y in zip(expected,b))
    return total**.5
