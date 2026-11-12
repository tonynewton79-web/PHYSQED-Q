"""Independent exact and adversarial tests for quadratic Forrelation."""
import random
import unittest
from fractions import Fraction
from physqed_q.quadratic_forrelation import (
    QuadraticPhase, _sum_quadratic_sign, exact_forrelation,
    independent_walsh_sum,
)


def phase_from_code(n: int, code: int) -> QuadraticPhase:
    pairs = tuple((i,j) for i in range(n) for j in range(i+1,n))
    taken = tuple(edge for k,edge in enumerate(pairs) if (code>>k)&1)
    t = len(pairs)
    linear = (code>>t) & ((1<<n)-1)
    c = (code>>(t+n)) & 1
    return QuadraticPhase(n, taken, linear, c)


class ForrelationExactTest(unittest.TestCase):
    def test_all_one_and_two_bit_inputs(self):
        for n in (1,2):
            count = 1 << (n*(n-1)//2 + n + 1)
            for a in range(count):
                f=phase_from_code(n,a)
                for b in range(count):
                    g=phase_from_code(n,b)
                    self.assertEqual(exact_forrelation(f,g).signed_sum,
                                     independent_walsh_sum(f,g))

    def test_random_independent_walsh(self):
        r=random.Random(20261112)
        for n, repetitions in ((3,300),(4,300),(5,200),(6,150),(7,70),(8,30)):
            count=1 << (n*(n-1)//2 + n + 1)
            for _ in range(repetitions):
                f=phase_from_code(n,r.randrange(count))
                g=phase_from_code(n,r.randrange(count))
                result=exact_forrelation(f,g)
                self.assertEqual(result.signed_sum, independent_walsh_sum(f,g))
                self.assertLessEqual(result.squared_amplitude, Fraction(1))
                self.assertEqual(result.radical_dimension % 2,0)

    def test_full_extremal_bent_quadratic_pair(self):
        for n in (2,4,6,8,10,16,32):
            Q=QuadraticPhase(n,tuple((i,i+1) for i in range(0,n,2)))
            p=exact_forrelation(Q,Q)
            self.assertEqual(p.signed_sum, 1 << (3*n//2))
            self.assertEqual(p.squared_amplitude,Fraction(1))
            self.assertEqual(p.radical_dimension,n)
            minus=QuadraticPhase(n,Q.pairs,constant=1)
            self.assertEqual(exact_forrelation(Q,minus).signed_sum,-p.signed_sum)

    def test_zero_result_and_negative_control(self):
        f=QuadraticPhase(2,((0,1),))
        g=QuadraticPhase(2,((0,1),),linear=1)
        self.assertEqual(exact_forrelation(f,g).signed_sum,0)
        self.assertEqual(independent_walsh_sum(f,g),0)
        g2=QuadraticPhase(2,(),linear=1)
        self.assertNotEqual(exact_forrelation(f,g2).signed_sum,0)

    def test_gauss_sum_direct_small(self):
        for m in (0,1,2,3,4):
            masks=[0]+[1<<i for i in range(m)]+[(1<<i)|(1<<j) for i in range(m) for j in range(i+1,m)]
            rng=random.Random(m+177)
            for _ in range(250):
                coeffs={masks[i] for i in range(len(masks)) if rng.randrange(2)}
                sign,expo,k=_sum_quadratic_sign(m,coeffs)
                brute=0
                for z in range(1<<m):
                    value=0
                    for term in coeffs:
                        if (z&term)==term:
                            value^=1
                    brute+=1 if value==0 else -1
                self.assertEqual((sign<<expo) if sign else 0,brute)
                self.assertEqual(k%2,m%2)

    def test_invalid_inputs(self):
        for kwargs in ({"n":0},{"n":2,"linear":4},{"n":2,"pairs":((0,0),)},
                       {"n":2,"pairs":((0,1),(0,1))},{"n":1,"constant":2}):
            with self.assertRaises(ValueError):
                QuadraticPhase(**kwargs)
        with self.assertRaises(ValueError):
            exact_forrelation(QuadraticPhase(2), QuadraticPhase(3))


if __name__=='__main__':
    unittest.main()
