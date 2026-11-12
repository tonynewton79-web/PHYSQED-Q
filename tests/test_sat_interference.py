"""End-to-end exact strong-simulation and adversarial approximation checks."""
import random
import unittest
from fractions import Fraction
from physqed_q.sat_interference import (
    compile_cnf, sat_count, direct_phase_gap, constraint_pairing_gap,
    recover_count_from_probability, hccz_program,
    additive_probability_approximation,
)


def sparse_hccz(total, basis, gates):
    """Independent sparse integer-amplitude H/CCZ simulator."""
    states={basis:1}
    hadamards=0
    for kind,indices in gates:
        new={}
        if kind=="H":
            hadamards+=1
            bit=1<<indices[0]
            for z,v in states.items():
                for dest,sign in ((z&~bit,1),(z|bit,(-1 if z&bit else 1))):
                    new[dest]=new.get(dest,0)+sign*v
        elif kind=="CCZ":
            mask=sum(1<<i for i in indices)
            for z,v in states.items():
                new[z]=(-v if (z&mask)==mask else v)
        else:
            raise AssertionError("invalid H/CCZ gate")
        states={z:v for z,v in new.items() if v}
    assert sum(v*v for v in states.values())==1<<hadamards
    return states,hadamards


class SatInterferenceTests(unittest.TestCase):
    def test_small_exact(self):
        cases=(
            (1,((1,),)),(1,((-1,),)),(1,((1,),(-1,))),
            (1,((1,-1),)),(2,((1,2),)),(2,((1,),(2,))),
            (2,((1,2),(-1,-2))),(3,((1,2,3),))
        )
        for n,clauses in cases:
            r=compile_cnf(n,clauses)
            s=sat_count(n,clauses)
            self.assertEqual(constraint_pairing_gap(r),s<<r.constraint_bits)
            self.assertEqual(direct_phase_gap(r),s<<r.constraint_bits)
            self.assertEqual(recover_count_from_probability(r,r.predicted_probability(s)),s)
            self.assertTrue(all(m.bit_count()<=3 for m in r.phase_monomials))

    def test_random_exact(self):
        rng=random.Random(2026111208)
        for n,reps in ((1,70),(2,100),(3,35)):
            for _ in range(reps):
                clauses=tuple(tuple((j if rng.randrange(2) else -j)
                                    for j in rng.sample(range(1,n+1),
                                                        rng.randrange(1,min(n,3)+1)))
                              for _ in range(rng.randrange(1,4)))
                r=compile_cnf(n,clauses)
                expected=sat_count(n,clauses)<<r.constraint_bits
                self.assertEqual(constraint_pairing_gap(r),expected)
                if r.phase_bits<=13:
                    self.assertEqual(direct_phase_gap(r),expected)

    def test_independent_hccz_state(self):
        for n,clauses in ((1,((1,),)),(1,((-1,),)),
                          (1,((1,),(-1,))),(2,((1,2),)),
                          (2,((1,),(2,))),(3,((1,2,3),))):
            r=compile_cnf(n,clauses)
            num,basis,gates,sign=hccz_program(r)
            self.assertEqual(num,r.phase_bits+2)
            self.assertEqual(sum(k=="H" for k,_ in gates),2*r.phase_bits)
            states,h=sparse_hccz(num,basis,gates)
            count=sat_count(n,clauses)
            self.assertEqual(sign*states.get(basis,0),count<<r.constraint_bits)
            self.assertEqual(Fraction(states.get(basis,0)**2,1<<h),
                             r.predicted_probability(count))

    def test_precision_and_tiny_gap(self):
        for n in range(1,9):
            r=compile_cnf(n,tuple((j,) for j in range(1,n+1)))
            self.assertEqual(sat_count(n,r.clauses),1)
            self.assertEqual(r.predicted_probability(1),
                             Fraction(1,1<<(2*(n+r.work_bits))))

    def test_unused_variables(self):
        for n in (1,2,10,120):
            r=compile_cnf(n,((1,),))
            answer=additive_probability_approximation(r,Fraction(1,1000))
            self.assertEqual(answer.estimate,Fraction(1,4))
            self.assertEqual(answer.enumerated_assignments,2)

    def test_random_additive_fptas(self):
        rng=random.Random(812007)
        epsilons=(Fraction(1),Fraction(1,4),Fraction(1,100),
                  Fraction(1,256),Fraction(1,65536),Fraction(1,10**8))
        for n,reps in ((1,40),(2,70),(3,60),(4,40)):
            for _ in range(reps):
                clauses=tuple(tuple((i if rng.randrange(2) else -i)
                                    for i in rng.sample(range(1,n+1),
                                               rng.randrange(1,min(n,3)+1)))
                              for _ in range(rng.randrange(1,5)))
                r=compile_cnf(n,clauses)
                truth=r.predicted_probability(sat_count(n,clauses))
                for eps in epsilons:
                    ans=additive_probability_approximation(r,eps)
                    self.assertLessEqual(abs(ans.estimate-truth),ans.maximum_absolute_error)
                    self.assertLessEqual(ans.maximum_absolute_error,eps)
                    if ans.method=="small_cone_exact":
                        self.assertEqual(ans.estimate,truth)
                        self.assertLessEqual(ans.relevant_inputs,r.work_bits+1)

    def test_malformed_inputs(self):
        for n,clauses in ((0,((1,),)),(1,()),(1,((0,),)),
                          (2,((3,),)),(2,((1,2,1,2),)),(1,((1.0,),))):
            with self.assertRaises(ValueError): compile_cnf(n,clauses)
        r=compile_cnf(2,((1,2),))
        with self.assertRaises(ValueError): direct_phase_gap(r,max_bits=1)
        for eps in (Fraction(0),Fraction(-1,3),Fraction(2),0.5):
            with self.assertRaises(ValueError):
                additive_probability_approximation(r,eps)
        for p in (Fraction(2,7),Fraction(-1,2),0.5):
            with self.assertRaises(ValueError):
                recover_count_from_probability(r,p)

    def test_hccz_gate_alphabet(self):
        for n,formula in ((1,((1,),)),(2,((1,2),)),(2,((1,),(-1,)))):
            r=compile_cnf(n,formula)
            wires,basis,gates,sign=hccz_program(r)
            self.assertTrue(all(k in ("H","CCZ") for k,_ in gates))
            self.assertEqual(basis,(3<<r.phase_bits))
            self.assertEqual(len(gates),2*r.phase_bits+len(r.phase_monomials))
            self.assertLessEqual(max(len(ids) for _,ids in gates),3)


if __name__=="__main__":
    unittest.main()
