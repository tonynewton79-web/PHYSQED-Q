"""Exact H+CCZ gadget checks against independent direct Toffoli permutation."""
import random
import unittest
from fractions import Fraction
from physqed_q.hccz_circuit import Gate, exact_run, compile_toffoli


class HcczTests(unittest.TestCase):
    def test_toffoli_exhaustive_basis(self):
        direct=(Gate('TOFFOLI',(0,1,2)),)
        compiled=compile_toffoli(direct)
        self.assertEqual(len(compiled),3)
        for basis in range(8):
            a=exact_run(3,direct,basis=basis,output=2)
            b=exact_run(3,compiled,basis=basis,output=2)
            self.assertEqual(a.output_probability,b.output_probability)
            self.assertEqual(tuple(z*2 for z in a.state_numerators),b.state_numerators)
            self.assertEqual(a.output_probability,Fraction(((basis>>2)&1)^int((basis&3)==3)))

    def test_random_mixed_circuit_exact(self):
        rng=random.Random(2026111205)
        for n,reps in ((3,120),(4,90),(5,60),(6,30)):
            for _ in range(reps):
                gates=[]
                for _ in range(rng.randrange(1,15)):
                    if rng.randrange(3):
                        gates.append(Gate('H',(rng.randrange(n),)))
                    else:
                        gate=rng.sample(range(n),3)
                        gates.append(Gate('TOFFOLI',tuple(gate)))
                direct=exact_run(n,gates,basis=rng.randrange(1<<n),output=rng.randrange(n))
                self.assertGreaterEqual(direct.output_probability,0)
                self.assertLessEqual(direct.output_probability,1)

    def test_random_mixed_circuit_compiled(self):
        rng=random.Random(6205)
        for n,reps in ((3,120),(4,100),(5,65),(6,40)):
            for _ in range(reps):
                gates=[]
                for _ in range(rng.randrange(1,14)):
                    if rng.randrange(2):
                        gates.append(Gate('H',(rng.randrange(n),)))
                    else:
                        gates.append(Gate('TOFFOLI',tuple(rng.sample(range(n),3))))
                basis=rng.randrange(1<<n)
                output=rng.randrange(n)
                a=exact_run(n,gates,basis=basis,output=output)
                b=exact_run(n,compile_toffoli(gates),basis=basis,output=output)
                self.assertEqual(a.output_probability,b.output_probability)
                self.assertEqual(tuple(v << ((b.hadamards-a.hadamards)//2) for v in a.state_numerators),b.state_numerators)

    def test_hadamard_coin_and_inverse(self):
        h=Gate('H',(0,))
        self.assertEqual(exact_run(1,(h,)).output_probability,Fraction(1,2))
        self.assertEqual(exact_run(1,(h,h)).output_probability,Fraction(0))
        self.assertEqual(exact_run(1,(h,h),basis=1).output_probability,Fraction(1))

    def test_refusal(self):
        for bad in ((Gate('CCZ',(0,0,1)),), (Gate('H',(3,)),),
                    (Gate('X',(0,)),),(Gate('TOFFOLI',(0,1)),)):
            with self.assertRaises(ValueError): exact_run(3,bad)
        with self.assertRaises(ValueError): exact_run(13,())

if __name__ == '__main__':
    unittest.main()
