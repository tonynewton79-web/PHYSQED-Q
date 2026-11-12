"""Exact public RSA/GL arithmetic, Fourier and 3-wire H-CCZ controls."""
import random
import unittest
from math import gcd
from fractions import Fraction
from physqed_q.rsa_hardcore import (
    RSAInput,parity_mask,toy_fixture,public_bit_toy,brute_inverse_toy,
    ideal_mask_truth_table,hadamard_spectrum_of_bit_oracle,
    finite_walsh_recover,hccz_phase_kickback_control
)
from physqed_q.hccz_circuit import exact_run

class RSAGLTests(unittest.TestCase):
    def test_all_public_masks_small_RSA(self):
        for p,q in ((3,5),(3,7),(5,7),(5,11),(7,11),(11,13)):
            N=p*q
            e=next(e for e in (3,5,7,11,17,19,65537) if gcd(e,(p-1)*(q-1))==1)
            for x in range(1,N):
                if gcd(x,N)!=1:continue
                for r in range(1<<N.bit_length()):
                    self.assertEqual(public_bit_toy(RSAInput(N,e,pow(x,e,N),r)),
                                     parity_mask(x,r))

    def test_independent_RSA_inversion(self):
        for p,q in ((3,5),(5,7),(5,11),(7,11),(11,13)):
            N=p*q
            phi=(p-1)*(q-1)
            e=next(e for e in (3,5,7,11) if gcd(e,phi)==1)
            d=pow(e,-1,phi)
            for x in range(1,N):
                if gcd(x,N)!=1:continue
                public=RSAInput(N,e,pow(x,e,N),1)
                self.assertEqual(pow(public.y,d,N),x)
                self.assertEqual(brute_inverse_toy(public),x)

    def test_all_secrets_Fourier_delta(self):
        for k in range(1,9):
            for x in range(1<<k):
                table=ideal_mask_truth_table(x,k)
                freq=hadamard_spectrum_of_bit_oracle(table)
                self.assertTrue(all(z==((1<<k) if i==x else 0)
                                    for i,z in enumerate(freq)))
                self.assertEqual(finite_walsh_recover(table),(x,Fraction(1)))

    def test_adversarial_20_percent_noise(self):
        rng=random.Random(20261112010)
        for k in range(3,9):
            N=1<<k
            flipped=max(1,N//5)
            for _ in range(15):
                x=rng.randrange(N)
                table=list(ideal_mask_truth_table(x,k))
                for i in rng.sample(range(N),flipped):table[i]^=1
                idx,corr=finite_walsh_recover(tuple(table))
                self.assertEqual(idx,x)
                self.assertEqual(corr,Fraction(N-2*flipped,N))

    def test_HCCZ_kickback_interference(self):
        n,g=hccz_phase_kickback_control()
        self.assertEqual(n,3)
        self.assertTrue(all(z.kind in ('H','CCZ') for z in g))
        self.assertEqual(exact_run(n,g,basis=6,output=0).output_probability,Fraction(1))
        self.assertEqual(exact_run(n,g,basis=4,output=0).output_probability,Fraction(0))

    def test_public_small_case_shortcuts(self):
        for p,q in ((3,5),(5,7),(11,13)):
            N=p*q
            e=next(e for e in range(3,30,2) if gcd(e,(p-1)*(q-1))==1)
            for x in range(1,N):
                if gcd(x,N)!=1:continue
                public,b=toy_fixture(p,q,e,x,0)
                self.assertEqual(b,0)
                self.assertEqual(public_bit_toy(public),0)
                self.assertEqual(brute_inverse_toy(public),x)

    def test_invalid_public_modulus(self):
        for args in ((15,2,1,3),(45,3,1,2),(25,3,1,1),
                     (15,3,0,1),(15,3,3,1),(27,5,1,3)):
            self.assertEqual(public_bit_toy(RSAInput(*args)),0)
        for args in ((14,3,1,0),(15,1,1,0),(15,3,15,0),
                     (15,3,1,16),(15,3,1,-1),(15,3,1,True)):
            with self.assertRaises(ValueError):RSAInput(*args)

    def test_refusals(self):
        for args in ((2.0,1),(2,-1),(True,1)):
            with self.assertRaises(ValueError):parity_mask(*args)
        large=RSAInput(65537,3,1,0)
        with self.assertRaises(ValueError):public_bit_toy(large)
        with self.assertRaises(ValueError):brute_inverse_toy(large)
        for bits in ((0,),(0,0,0),(0,1,2,1),tuple([0]*(1<<13))):
            with self.assertRaises(ValueError):hadamard_spectrum_of_bit_oracle(bits)

if __name__=='__main__':
    unittest.main()
