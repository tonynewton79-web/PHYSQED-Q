"""Exact three-edge triangle phase predicate through PHYSQED-Q.

Not an adjacency-query algorithm and NOT evidence of an O(n) quantum
query bound for triangle finding. The 3 edge values are preloaded.
"""
import unittest
from physqed_q.kernel import (
    CircuitError, ONE, NEG_ONE, ZERO, unitary, validate_circuit)
from physqed_q.compiler import compile_circuit, verify_receipt


def triangle_ccz():
    gates=[]
    def add(name,*indices):
        gates.append({"gate":name,"qubits":list(indices)})
    for qubit in range(3):
        add("T",qubit)
    for control,target in ((0,1),(0,2),(1,2)):
        add("CNOT",control,target)
        add("TDG",target)
        add("CNOT",control,target)
    add("CNOT",0,2);add("CNOT",1,2)
    add("T",2)
    add("CNOT",1,2);add("CNOT",0,2)
    return {"name":"three-edge-bits-triangle-phase-CCZ","qubits":3,"gates":gates}


class TrianglePhaseScope(unittest.TestCase):
    def test_every_matrix_element_is_exact(self):
        circuit=validate_circuit(triangle_ccz())
        self.assertEqual(len(circuit["gates"]),17)
        cols=unitary(circuit)
        self.assertEqual(len(cols),8)
        for column in range(8):
            for row in range(8):
                expected=NEG_ONE if row==column==7 else (
                    ONE if row==column else ZERO)
                self.assertEqual(cols[column][row],expected)

    def test_receipt_replay(self):
        receipt=compile_circuit(triangle_ccz())
        self.assertIsInstance(verify_receipt(receipt),dict)

    def test_mutated_circuit_is_detected(self):
        good=triangle_ccz()
        corrupted={**good,"gates":good["gates"][:-1]}
        self.assertNotEqual(unitary(good),unitary(corrupted))

    def test_unimplemented_three_body_gate_is_refused(self):
        with self.assertRaises(CircuitError):
            validate_circuit({"name":"unsupported CCZ","qubits":3,
              "gates":[{"gate":"CCZ","qubits":[0,1,2]}]})


if __name__=="__main__":
    unittest.main()
