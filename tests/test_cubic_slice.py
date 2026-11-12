"""Exact randomized, adversarial, and high-density factor-rank tests."""
import random
import unittest
from fractions import Fraction
from itertools import combinations
from physqed_q.cubic_slice import (Phase, complete_cubic, exact_forrelation,
                                    independent_walsh, quadratic_sign_sum)


class CubicSliceTests(unittest.TestCase):
    def test_complete_hypergraph_identity(self):
        for n in range(3, 13):
            p = complete_cubic(n)
            expected = tuple(sorted(sum(1 << i for i in triple) for triple in combinations(range(n), 3)))
            self.assertEqual(p.expanded_anf(), expected)
            if n <= 10:
                for x in range(1 << n):
                    self.assertEqual(p.evaluate(x), (x.bit_count() % 4 == 3))

    def test_random_factors_independent_walsh(self):
        rng = random.Random(2026111205)
        for n, cases in ((1, 80), (2, 90), (3, 100), (4, 120), (5, 120),
                         (6, 100), (7, 60), (8, 40)):
            masks = [m for m in range(1 << n) if m.bit_count() <= 2]
            def sample():
                base = tuple(m for m in masks if rng.randrange(2))
                factors = tuple((rng.randrange(1, 1 << n),
                                 tuple(m for m in masks if rng.randrange(2)))
                                for _ in range(rng.randrange(3)))
                return Phase(n, base, factors)
            for _ in range(cases):
                p, q = sample(), sample()
                cert = exact_forrelation(p, q)
                direct = independent_walsh(p, q)
                self.assertEqual(cert.signed_sum, direct)
                self.assertEqual(cert.probability, Fraction(direct ** 2, 1 << (3*n)))
                self.assertLessEqual(cert.probability, 1)

    def test_dense_hard_graph_but_rank_one(self):
        for n in (3, 4, 5, 6, 8, 10, 12):
            p = complete_cubic(n)
            got = exact_forrelation(p, p)
            self.assertEqual(got.factor_count, 2)
            self.assertEqual(got.gaussian_branches, 16)
            self.assertEqual(got.signed_sum, independent_walsh(p, p))
        for n in (24, 48, 72):
            p = complete_cubic(n)
            got = exact_forrelation(p, p)
            self.assertEqual(got.gaussian_branches, 16)
            self.assertLessEqual(got.probability, 1)

    def test_zero_and_sign(self):
        n=3
        p=complete_cubic(n)
        t=exact_forrelation(p,p)
        minus=Phase(n,(0,),p.factors)
        self.assertEqual(exact_forrelation(p,minus).signed_sum,-t.signed_sum)
        self.assertEqual(exact_forrelation(Phase(1),Phase(1)).signed_sum,2)

    def test_gauss_sum_brute_force(self):
        rng=random.Random(17719)
        for n in range(1,8):
            all_m=[m for m in range(1<<n) if m.bit_count()<=2]
            for _ in range(60):
                terms=tuple(m for m in all_m if rng.randrange(2))
                want=sum(1-2*(sum((x&m)==m for m in terms)&1) for x in range(1<<n))
                self.assertEqual(quadratic_sign_sum(n,terms),want)

    def test_validation_and_budget(self):
        with self.assertRaises(ValueError): Phase(3, (7,))
        with self.assertRaises(ValueError): Phase(3, factors=((0,(1,)),))
        with self.assertRaises(ValueError): Phase(2, (1,1))
        with self.assertRaises(ValueError): exact_forrelation(complete_cubic(3),complete_cubic(3),max_factors=1)
        with self.assertRaises(ValueError): exact_forrelation(Phase(3), Phase(4))

if __name__ == '__main__':
    unittest.main()
