"""Exact public-input MOD3 H/CCZ verification and destruction controls."""
import random
import unittest
from fractions import Fraction
from physqed_q.public_mod3 import (
    public_mod3_circuit,input_basis,transition,streaming_mod3,
    prefix_residuals_witness,uniform_description_query_ceiling,
)
from physqed_q.hccz_circuit import exact_run


class PublicMod3Tests(unittest.TestCase):
    def test_all_four_transition_states(self):
        for a in range(2):
            for b in range(2):
                self.assertEqual(transition(a,b,0),(a,b))
                self.assertEqual(transition(a,b,1),(b,a^b))
                self.assertEqual(transition(*transition(*transition(a,b,1),1),1),(a,b))

    def test_full_hccz_exhaustive_inputs_up_to_six(self):
        count=0
        for n in range(1,7):
            spec=public_mod3_circuit(n)
            for x in range(1<<n):
                out=exact_run(n+4,spec.gates,basis=input_basis(n,x),output=n+1)
                expected=int(x.bit_count()%3==0)
                self.assertEqual(out.output_probability,Fraction(expected))
                self.assertEqual(streaming_mod3(n,x),expected)
                a,b=1,0
                for i in range(n):
                    a,b=transition(a,b,(x>>i)&1)
                final=input_basis(n,x)|(a<<n)|((b^1)<<(n+1))
                self.assertEqual(sum(v!=0 for v in out.state_numerators),1)
                self.assertEqual(out.state_numerators[final],1<<(spec.hadamards//2))
                count+=1
        self.assertEqual(count,126)

    def test_eight_input_bits_boundary_controls(self):
        n=8
        spec=public_mod3_circuit(n)
        for x in (0,1,2,3,7,31,63,85,127,170,254,255):
            out=exact_run(n+4,spec.gates,basis=input_basis(n,x),output=n+1)
            self.assertEqual(out.output_probability,Fraction(int(x.bit_count()%3==0)))

    def test_uniformity_and_gate_counts(self):
        for n in (1,2,3,5,8,32,128,1024):
            p=public_mod3_circuit(n)
            self.assertEqual((len(p.gates),p.hadamards,p.cczs),
                             (6*n+6,4*n+4,2*n+2))
            self.assertEqual(p.total_qubits,n+4)
            self.assertTrue(all(g.kind in ('H','CCZ') for g in p.gates))
            self.assertLess(uniform_description_query_ceiling(n),300*n*n)
            if n<=8:
                self.assertEqual(p.gates,public_mod3_circuit(n).gates)

    def test_large_classical_decoder_adversarial(self):
        rng=random.Random(2026111207)
        for n in (1,3,8,32,101,255,1024,4096):
            for _ in range(120):
                x=rng.getrandbits(n)
                self.assertEqual(streaming_mod3(n,x),int(x.bit_count()%3==0))

    def test_width_three_is_sharp(self):
        for n in range(4,45):
            for k in range(2,n-1):
                matrix=prefix_residuals_witness(n,k)
                self.assertEqual(matrix,((1,0,0),(0,0,1),(0,1,0)))

    def test_corrupted_gate_sequence_fails(self):
        n=4
        p=public_mod3_circuit(n)
        # Delete one three-gate Toffoli block from the first input stage.
        bad=p.gates[:3]+p.gates[6:]
        differences=0
        for x in range(1<<n):
            out=exact_run(n+4,bad,basis=input_basis(n,x),output=n+1)
            differences+=out.output_probability!=int(x.bit_count()%3==0)
        self.assertGreater(differences,0)

    def test_input_validation(self):
        for n in (0,-1,1.1,True):
            with self.assertRaises(ValueError):
                public_mod3_circuit(n)
        for a in ((2,4),(2,-1),(0,0),(2,1.0)):
            with self.assertRaises(ValueError):
                input_basis(*a)
        for a in ((2,0,1),(1,True,0),(0,1,-1)):
            with self.assertRaises(ValueError):
                transition(*a)
        for a in ((3,2),(6,5)):
            with self.assertRaises(ValueError):
                prefix_residuals_witness(*a)


if __name__=='__main__':
    unittest.main()
