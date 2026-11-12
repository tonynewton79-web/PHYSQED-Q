"""Regression tests for a restricted, exact scalar signal-processing bound."""
import random
import unittest
from fractions import Fraction
from physqed_q.attack009_gap import (
    grover_probability, required_grover_iterations_by_quadratic_bound,
    required_polynomial_degree_by_markov, certify_unique_sat_barrier,
    toy_hccz_interference_circuits,
)
from physqed_q.hccz_circuit import exact_run
from physqed_q.sat_interference import compile_cnf, sat_count


class GapTests(unittest.TestCase):
    def test_grover_exact_first_two(self):
        rng=random.Random(2026111209)
        for _ in range(200):
            p=Fraction(rng.randrange(1001),1000)
            self.assertEqual(grover_probability(p,0),p)
            self.assertEqual(grover_probability(p,1),p*(3-4*p)**2)

    def test_certified_upper_bound(self):
        for s in range(1,11):
            p=Fraction(1,1<<(2*s))
            for k in range(40):
                self.assertLessEqual(grover_probability(p,k),
                                     min(Fraction(1),(2*k+1)**2*p))

    def test_bound_rounding_exact(self):
        threshold=Fraction(2,3)
        for n in range(1,11):
            for w in range(11):
                k=required_grover_iterations_by_quadratic_bound(n,w,threshold)
                p=Fraction(1,1<<(2*(n+w)))
                self.assertGreaterEqual((2*k+1)**2*p,threshold)
                if k:
                    self.assertLess((2*k-1)**2*p,threshold)

    def test_markov_rounding_exact(self):
        for n in range(1,13):
            for w in range(12):
                d=required_polynomial_degree_by_markov(n,w)
                p=Fraction(1,1<<(2*(n+w)))
                self.assertGreaterEqual(2*d*d*p,Fraction(1,3))
                if d:
                    self.assertLess(2*(d-1)**2*p,Fraction(1,3))

    def test_unit_cnf_unique_sat(self):
        for n in range(1,13):
            r=compile_cnf(n,tuple((i,) for i in range(1,n+1)))
            self.assertEqual(sat_count(n,r.clauses),1)
            self.assertEqual(r.work_bits,n-1)
            b=certify_unique_sat_barrier(n,r.work_bits)
            self.assertEqual(b.raw_unique_sat_probability,r.predicted_probability(1))
            self.assertFalse(b.unrestricted_lower_bound_proved)

    def test_exact_interference_constant_gap(self):
        c=toy_hccz_interference_circuits()
        no=exact_run(c["n_wires"],c["no"],basis=c["basis"])
        yes=exact_run(c["n_wires"],c["yes"],basis=c["basis"])
        self.assertEqual(no.output_probability,Fraction(1,4))
        self.assertEqual(yes.output_probability,Fraction(3,4))

    def test_refusals(self):
        for p in (1,0.5,Fraction(-1,3),Fraction(4,3)):
            with self.assertRaises(ValueError):grover_probability(p,1)
        for k in (-1,1.0,True):
            with self.assertRaises(ValueError):grover_probability(Fraction(1,4),k)
        for args in ({"n":0,"work_bits":0},{"n":2,"work_bits":-1}):
            with self.assertRaises(ValueError):certify_unique_sat_barrier(**args)
        for t in (0,Fraction(4,3),0.5):
            with self.assertRaises(ValueError):
                required_grover_iterations_by_quadratic_bound(1,0,t)



    def test_postselection_rational_falsifier(self):
        from physqed_q.attack009_gap import postselection_rational_bypass
        for n in range(1,16):
            delta=Fraction(1,1<<(2*(2*n-1)))
            no=postselection_rational_bypass(Fraction(0),delta)
            yes=postselection_rational_bypass(delta,delta)
            self.assertEqual(no.conditional_acceptance,0)
            self.assertEqual(yes.conditional_acceptance,Fraction(2,3))
            self.assertEqual(no.selection_probability,delta/4)
            self.assertEqual(yes.selection_probability,3*delta/4)
            self.assertEqual(no.expected_independent_trials,Fraction(4)/delta)
            for count in (1,2,3,5):
                p=count**2*delta
                if p<=1:
                    self.assertGreaterEqual(postselection_rational_bypass(p,delta).conditional_acceptance,Fraction(2,3))
        with self.assertRaises(ValueError):
            postselection_rational_bypass(Fraction(1,2),Fraction(0))
        with self.assertRaises(ValueError):
            postselection_rational_bypass(0.5,Fraction(1,4))

if __name__=="__main__":
    unittest.main()
