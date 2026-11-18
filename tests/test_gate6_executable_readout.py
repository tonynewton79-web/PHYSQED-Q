"""Gate 6 deterministic shortest SWAP routing and locked research scope."""
import unittest
from benchmarks.gate6_executable_readout import (
    token_route, CASE_IDS, OUTPUT_RULES, BACKEND_IDS,
    derive_positions, IDEAL_TOL
)
from benchmarks.gate3_applications import corpus


def move(positions,edges):
    current=list(positions)
    for a,b in edges:
        current=[b if q==a else a if q==b else q for q in current]
    return tuple(current)


class Gate6SwapRoutingTests(unittest.TestCase):
    def test_fixed_posthoc_scope_and_two_output_assignments(self):
        self.assertEqual(len(CASE_IDS),5)
        self.assertEqual(len(set(CASE_IDS)),5)
        self.assertTrue(set(CASE_IDS).issubset({c["name"] for c in corpus()}))
        self.assertEqual(OUTPUT_RULES,("identity","reverse"))
        self.assertEqual(BACKEND_IDS,("fake_manila","fake_lagos"))
        self.assertLess(IDEAL_TOL,1e-6)

    def test_single_swap_and_no_op(self):
        edges=((0,1),(1,2))
        self.assertEqual(token_route((0,2,1),(0,1,2),edges),[(1,2)])
        self.assertEqual(token_route((0,1,2),(0,1,2),edges),[])
        self.assertEqual(token_route((1,0),(0,1),edges),[(0,1)])

    def test_reversal_on_line_with_unmeasured_positions(self):
        edges=((0,1),(1,2),(2,3),(3,4))
        for src,dst in (
            ((0,1,2),(2,1,0)), ((1,3,2),(0,1,2)),
            ((4,1,3),(2,1,0)),((0,1,2,3),(3,2,1,0)),
        ):
            with self.subTest(src=src,dst=dst):
                path=token_route(src,dst,edges)
                self.assertEqual(move(src,path),dst)
                self.assertTrue(all(tuple(sorted(edge)) in edges for edge in path))
                self.assertLess(len(path),80)

    def test_reject_invalid_registers_and_disconnected(self):
        for src,dst,edges in (
            ((0,0),(0,1),((0,1),)),
            ((0,1),(0,0),((0,1),)),
            ((0,1),(0,2),((0,1),)),
            ((0,1),(0,1),()),
        ):
            with self.subTest(src=src,dst=dst):
                with self.assertRaises(ValueError):
                    token_route(src,dst,edges)
        with self.assertRaises(RuntimeError):
            token_route((0,1),(2,3),((0,1),(2,3)))

    def test_physical_measurement_destinations_from_qiskit(self):
        from qiskit import QuantumCircuit
        qc=QuantumCircuit(5,3)
        qc.measure(2,0)
        qc.measure(0,1)
        qc.measure(4,2)
        self.assertEqual(derive_positions(qc,3),(2,0,4))
        qc.measure(1,1)
        with self.assertRaises(RuntimeError):
            derive_positions(qc,3)


if __name__=="__main__":
    unittest.main()
