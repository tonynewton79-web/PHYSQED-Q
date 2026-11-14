"""Exact end-to-end validation of the uniform modular-exponentiation core."""
import unittest
from fractions import Fraction
from math import gcd
from physqed_q.modexp_core import (
    compile_modexp_core, sparse_integer_state, decoded_modexp_state,
    exact_walsh_marginal, order_toy,
)


class ModexpCoreTests(unittest.TestCase):
    def test_clean_modexp_exhaustive_small_public_moduli(self):
        for N in (5,7,8,9,11,15,16,21,25,27,35):
            for a in range(2,min(N,9)):
                if gcd(a,N)!=1: continue
                for m in (1,2,3):
                    c=compile_modexp_core(N,a,m)
                    state,h=sparse_integer_state(c)
                    joint=decoded_modexp_state(c,state,h)
                    expected={(x,pow(a,x,N)):Fraction(1,1<<m)
                              for x in range(1<<m)}
                    self.assertEqual(joint,expected,(N,a,m))
                    self.assertEqual(sum(joint.values()),1)
                    self.assertTrue(all(g.kind in ('H','CCZ') for g in c.gates))
                    self.assertEqual(c.gate_count,len(c.gates))
                    self.assertEqual(c.hadamard_count,
                                     sum(g.kind=='H' for g in c.gates))
                    self.assertEqual(c.hadamard_count,m+2*c.toffoli_count)

    def test_walsh_end_to_end_generic_moduli(self):
        for N,a,m in ((5,2,4),(7,3,4),(9,2,4),(15,2,4),
                      (16,5,4),(21,2,4),(25,2,4),(27,2,4)):
            c=compile_modexp_core(N,a,m,include_final_hadamards=True)
            state,h=sparse_integer_state(c)
            joint=decoded_modexp_state(c,state,h,final_hadamards=True)
            got={z:sum(prob for (w,_),prob in joint.items() if w==z)
                 for z in range(1<<m)}
            self.assertEqual(got,exact_walsh_marginal(a,N,m))
            self.assertEqual(sum(got.values()),1)

    def test_power_two_order_schmidt_and_marginal(self):
        for s in range(3,9):
            N=1<<s
            t=s-2
            self.assertEqual(order_toy(5,N),1<<t)
            for m in (t,s):
                c=compile_modexp_core(N,5,m,include_final_hadamards=True)
                state,h=sparse_integer_state(c)
                joint=decoded_modexp_state(c,state,h,final_hadamards=True)
                r=1<<t
                for z in range(1<<m):
                    marginal=sum(prob for (w,_),prob in joint.items() if w==z)
                    self.assertEqual(marginal,Fraction(int(z<r),r))
                self.assertEqual(len(joint),r*r)
                self.assertTrue(all(prob==Fraction(1,r*r)
                                    for prob in joint.values()))

    def test_non_power_two_period_is_different(self):
        self.assertEqual(order_toy(2,21),6)
        marginal=exact_walsh_marginal(2,21,4)
        self.assertEqual(marginal[0],Fraction(11,64))
        self.assertEqual(marginal[14],Fraction(9,64))
        self.assertNotEqual(len(set(marginal.values())),1)

    def test_cleans_ancillas_with_repeated_output(self):
        for N,a,m in ((15,2,5),(16,5,5),(21,2,5)):
            c=compile_modexp_core(N,a,m)
            state,h=sparse_integer_state(c)
            self.assertEqual(len(state),1<<m)
            joint=decoded_modexp_state(c,state,h)
            self.assertEqual(sum(joint.values()),1)
            self.assertEqual(len(c.work_wires),c.n_wires-m-3-c.data_bits)

    def test_polynomial_gate_growth_and_no_truth_tables(self):
        for s in range(3,18):
            modulus=1<<s
            m=s
            c=compile_modexp_core(modulus,5,m)
            self.assertLess(c.gate_count,100*m*s**3)
            self.assertLess(c.n_wires,100*m*s**3)
            self.assertEqual(c.toffoli_count,(c.gate_count-m)//3)
            self.assertEqual(sum(g.kind=='CCZ' for g in c.gates),c.toffoli_count)

    def test_refusals_and_explicit_scope(self):
        for args in ((0,2,1),(2,1,1),(9,3,2),(15,15,2),
                     (16,5,0),(15,2,1.5),(True,2,3)):
            with self.assertRaises(ValueError):compile_modexp_core(*args)
        c=compile_modexp_core(16,5,3)
        with self.assertRaises(ValueError):sparse_integer_state(c,maximum_support=2)
        with self.assertRaises(ValueError):order_toy(5,10001)
        with self.assertRaises(ValueError):exact_walsh_marginal(5,16,10)


if __name__=='__main__':
    unittest.main()
