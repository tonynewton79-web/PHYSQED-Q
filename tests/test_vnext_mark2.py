"""Independent full 2^n operator tests of the own Mark II physical router."""
from copy import deepcopy
from fractions import Fraction
import random
import unittest

from physqed_q.vnext import VNextError, _hash
from physqed_q.vnext_mark2 import (
    compile_mark2, verify_mark2, shortest_swaps, validate_error_envelope,
)
from physqed_q.vnext_numeric import numeric_unitary, _evolve


def example_target(n=4,*,chain=True,native_swap=False):
    edges=([[i,i+1] for i in range(n-1)] if chain else
           [[a,b] for a in range(n) for b in range(a+1,n)])
    alphabet=sorted(["H","X","Z","S","SDG","T","TDG","RZPI",
                     "CNOT","CZ"]+(["SWAP"] if native_swap else []))
    target={"name":"OWN_MARK_II_SYNTHETIC_TARGET","qubits":n,
            "couplings":edges,"native_gates":alphabet,
            "one_qubit_fault":"0","two_qubit_fault":"0",
            "readout_faults":["0"]*n,"provenance":"synthetic"}
    envelope={"one_qubit_fault_upper":["1/1000"]*n,
              "two_qubit_fault_upper_by_edge":[[a,b,"1/200"] for a,b in edges],
              "readout_fault_upper":["1/50"]*n,
              "fault_semantics":"marginal_fault_event_upper_bounds",
              "provenance":"synthetic"}
    return target,envelope


def example(n=4):
    return {"name":"mark2-verification","qubits":n,"gates":[
        {"gate":"H","qubits":[0]},
        {"gate":"CNOT","qubits":[0,n-1]},
        {"gate":"RZPI","qubits":[1],"angle_pi":"1/3"},
        {"gate":"CNOT","qubits":[1,2]},
    ] if n>=3 else [
        {"gate":"H","qubits":[0]},
        {"gate":"CNOT","qubits":[0,1]}
    ]}


def matrix_check(receipt):
    """Independent native-statevector check across all basis inputs.

    Map the lowering result to its initial physical wires and apply the
    final wire permutation, then compare with the actual Mark II circuit.
    This is a numeric independent control, not Lean or formal verification.
    """
    n=receipt["native_circuit"]["qubits"]
    initial=receipt["physical_initial_logical_layout"]
    original=receipt["virtual_lowering_receipt"]["compiled"]["gates"]
    reference={"name":"logical-unrouted","qubits":n,"gates":[
        {**{k:v for k,v in gate.items() if k!="qubits"},
         "qubits":[initial[q] for q in gate["qubits"]]}
        for gate in original
    ]}
    def full_matrix(program):
        if len(program["gates"])<=512:
            return numeric_unitary(program,expanded_native=True)
        if len(program["gates"])>4096:
            raise VNextError("numeric verification exceeds Mark II gate bound")
        return [_evolve(program,j) for j in range(1<<n)]
    U=full_matrix(reference)
    V=full_matrix(receipt["native_circuit"])
    perm=receipt["end_permutation_of_input_wire_states"]
    if sorted(perm)!=list(range(n)):
        raise VNextError("invalid reference permutation")
    error=0.
    for col_a,col_b in zip(U,V):
        expected=[0j]*(1<<n)
        for index,amplitude in enumerate(col_a):
            j=sum(((index>>wire)&1)<<new for wire,new in enumerate(perm))
            expected[j]=amplitude
        error+=sum(abs(x-y)**2 for x,y in zip(expected,col_b))
    return error**.5


class MarkIITest(unittest.TestCase):
    def test_nonlocal_routing_with_three_cnot_swap_decomposition(self):
        t,e=example_target()
        receipt=compile_mark2(
            example(),t,e,
            required_physical_qubits_for_classical_bits=[3,2,1,0],
            max_projective_error="0")
        self.assertEqual(receipt["physical_final_logical_layout"],[3,2,1,0])
        self.assertGreater(receipt["cost"]["inserted_local_swaps"],0)
        self.assertGreaterEqual(
            receipt["cost"]["physical_native_two_qubit"],
            3*receipt["cost"]["inserted_local_swaps"])
        self.assertTrue(verify_mark2(receipt)["verified"])
        self.assertLess(matrix_check(receipt),1e-11)

    def test_native_swap_cost_and_full_operator(self):
        t,e=example_target(native_swap=True)
        r=compile_mark2(
            example(),t,e,
            required_physical_qubits_for_classical_bits=[3,2,1,0],
            max_projective_error="0")
        self.assertEqual(
            r["cost"]["physical_native_two_qubit"],
            r["cost"]["inserted_local_swaps"]+2)
        self.assertLess(matrix_check(r),1e-11)

    def test_nonidentity_classical_bit_output_map(self):
        t,e=example_target(3)
        r=compile_mark2(
            {"name":"permuted-readout","qubits":3,"gates":[
                {"gate":"H","qubits":[0]},
                {"gate":"CNOT","qubits":[0,2]}]},
            t,e,
            classical_output_bit_to_logical_qubit=[2,0,1],
            required_physical_qubits_for_classical_bits=[1,2,0],
            max_projective_error="0")
        self.assertEqual(
            [m["physical_qubit"] for m in r["physical_output_measurements"]],
            [1,2,0])
        self.assertEqual(
            [m["logical_qubit"] for m in r["physical_output_measurements"]],
            [2,0,1])
        self.assertLess(matrix_check(r),1e-11)

    def test_correlated_fault_union_upper_bound(self):
        t,e=example_target(3)
        r=compile_mark2(
            {"name":"noise-control","qubits":3,"gates":[
                {"gate":"H","qubits":[1]},
                {"gate":"CZ","qubits":[0,1]}]},
            t,e,max_projective_error="0")
        cost=r["cost"]
        expected=(Fraction(cost["physical_native_one_qubit"],1000)+
                  Fraction(cost["physical_native_two_qubit"],200)+
                  Fraction(3,50))
        self.assertEqual(
            Fraction(r["correlation_robust_marginal_fault_union_bound"]),
            min(Fraction(1),expected))
        self.assertEqual(Fraction(r["logical_projective_operator_bound"]),0)

    def test_refuse_disconnected_unsupported_and_bad_fault_model(self):
        t,e=example_target(3)
        t["couplings"]=[[0,1]]
        e["two_qubit_fault_upper_by_edge"]=[[0,1,"1/100"]]
        with self.assertRaisesRegex(
            VNextError,"NO_PHYSICALLY_CONNECTED_ROUTING_PATH"):
            compile_mark2(
                {"name":"disconnected","qubits":3,"gates":[
                    {"gate":"CNOT","qubits":[0,2]}]},
                t,e,max_projective_error="0")
        t,e=example_target(3)
        t["native_gates"].remove("CNOT")
        with self.assertRaises(VNextError):
            compile_mark2(example(3),t,e,max_projective_error="0")
        t,e=example_target(3)
        e["fault_semantics"]="unproved noise channel"
        with self.assertRaises(VNextError):
            validate_error_envelope(e,t)
        t,e=example_target(3)
        t["one_qubit_fault"]="1/100"
        with self.assertRaisesRegex(VNextError,"USE_MARK2_HETEROGENEOUS_ENVELOPE"):
            compile_mark2(example(3),t,e,max_projective_error="0")

    def test_tampering_rehashed_false_gate_cost_or_hardware_claim(self):
        t,e=example_target(3)
        good=compile_mark2(example(3),t,e,max_projective_error="0")
        for forged in ("cost","claim_scope"):
            altered=deepcopy(good)
            if forged=="cost":
                altered["cost"]["physical_native_two_qubit"]=0
            else:
                altered["claim_scope"]["hardware_execution_performed"]=True
            altered["receipt_sha256"]=_hash(
                {k:v for k,v in altered.items() if k!="receipt_sha256"})
            with self.assertRaises(VNextError):
                verify_mark2(altered)

    def test_deterministic_bfs_six_swaps_to_reverse_line(self):
        p=[0,1,2,3]
        path=shortest_swaps(tuple(p),((0,1),(1,2),(2,3)),
                             lambda s:s==(3,2,1,0))
        for a,b in path:
            p=[b if q==a else a if q==b else q for q in p]
        self.assertEqual(p,[3,2,1,0])
        self.assertEqual(len(path),6)

    def test_forty_randomized_complete_native_operator_controls(self):
        rng=random.Random(20261118)
        for k in range(40):
            n=rng.choice((2,3,4))
            src={"name":"MarkII-random-"+str(k),"qubits":n,"gates":[]}
            for _ in range(rng.randint(2,12)):
                kind=rng.choice(("H","X","T","RZPI","CNOT","CZ","SWAP"))
                q=rng.sample(range(n),2) if kind in ("CNOT","CZ","SWAP") else [
                    rng.randrange(n)]
                op={"gate":kind,"qubits":q}
                if kind=="RZPI":
                    op["angle_pi"]=rng.choice(("1/3","-2/7","0","-1/4"))
                src["gates"].append(op)
            t,e=example_target(n,native_swap=True)
            initial=rng.sample(range(n),n)
            output=rng.sample(range(n),n)
            classical=rng.sample(range(n),n)
            r=compile_mark2(
                src,t,e,
                initial_logical_to_physical=initial,
                classical_output_bit_to_logical_qubit=classical,
                required_physical_qubits_for_classical_bits=output,
                max_projective_error="0")
            with self.subTest(random_circuit=k):
                self.assertEqual(
                    [m["physical_qubit"] for m in r["physical_output_measurements"]],
                    output)
                self.assertTrue(verify_mark2(r)["verified"])
                self.assertLess(matrix_check(r),2e-10)


if __name__=="__main__":
    unittest.main()
