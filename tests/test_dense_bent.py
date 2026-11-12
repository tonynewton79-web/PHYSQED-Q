"""Exact tests: dense cubic perfect-gap family and public-dual sampling."""
import math
import random
import unittest
from fractions import Fraction
from physqed_q.cubic_bandwidth import (
    CubicPhase, independent_walsh_sum, relabel_phase, exact_banded_forrelation,
)
from physqed_q.dense_bent import (
    quadratic_controls, quadratic_vector, pi_involution, make_pair,
    direct_p, direct_g, classify_explicit_pair, all_linear_tilt_numerators,
    verify_mask_parseval, three_query_classical_tilt_test, public_dual_sample_mean,
)


class DenseBentTests(unittest.TestCase):
    def test_involution(self):
        for r in range(2,7):
            for y in range(1<<(2*r)):
                self.assertEqual(pi_involution(r,pi_involution(r,y)),y)
                self.assertLess(quadratic_vector(r,y&((1<<r)-1)),1<<r)

    def test_anf_matches_direct_definition(self):
        rng=random.Random(2026111204)
        for r in (2,3,4):
            n=4*r
            configs=[(0,False),(1,False),(1<<(n-1),True),
                     (rng.randrange(1<<n),False)]
            for tilt,flip in configs:
                p,g=make_pair(r,tilt=tilt,sign_flip=flip)
                sample=(range(1<<n) if r==2 else
                        [rng.randrange(1<<n) for _ in range(300)])
                for z in sample:
                    self.assertEqual(p.evaluate(z),direct_p(r,z))
                    self.assertEqual(g.evaluate(z),direct_g(r,z,tilt,flip))

    def test_exact_quantum_probability(self):
        rng=random.Random(407)
        for r,trials in ((2,15),(3,18),(4,3)):
            n=4*r
            tilts=[0,1,1<<(n-1)]+[rng.randrange(1<<n) for _ in range(trials)]
            for tilt in tilts:
                p,g=make_pair(r,tilt=tilt)
                out=classify_explicit_pair(r,p,g)
                self.assertEqual(independent_walsh_sum(p,g),
                                 (1<<(3*n//2)) if tilt==0 else 0)
                self.assertEqual(out.decision,"YES" if tilt==0 else "NO")
                self.assertEqual(out.quantum_zero_probability,Fraction(tilt==0))

    def test_full_mask_parseval_and_extremal_delta(self):
        p,g=make_pair(2)
        nums=all_linear_tilt_numerators(p,g)
        self.assertEqual(nums[0],1<<12)
        self.assertEqual(nums[1:],[0]*255)
        self.assertTrue(verify_mask_parseval(p,g))
        rng=random.Random(819)
        for n in range(1,9):
            masks=[m for m in range(1<<n) if m.bit_count()<=3]
            for _ in range(12):
                f=CubicPhase(n,tuple(m for m in masks if rng.randrange(2)))
                h=CubicPhase(n,tuple(m for m in masks if rng.randrange(2)))
                self.assertTrue(verify_mask_parseval(f,h))
                vals=all_linear_tilt_numerators(f,h)
                self.assertEqual(sum(s*s for s in vals),1<<(3*n))

    def test_dense_clique_and_classical_decider(self):
        for r in (2,3,6,12,20):
            p,g=make_pair(r)
            cert=classify_explicit_pair(r,p,g)
            self.assertEqual(cert.n,4*r)
            self.assertEqual(cert.primal_clique_size,r)
            self.assertEqual(cert.treewidth_lower_bound,r-1)
            self.assertEqual(cert.all_order_bandwidth_lower_bound,r)
            self.assertGreaterEqual(cert.cubic_terms_per_phase,
                                    ((r+1)//2)*math.comb(r,2))
            self.assertTrue(all((i,k) in quadratic_controls(r)[0]
                                for i in range(r) for k in range(i+1,r)))
            self.assertEqual(cert.decision,"YES")
            self.assertEqual(classify_explicit_pair(r,p,make_pair(r,tilt=3)[1]).decision,"NO")
            if r>=6:
                with self.assertRaises(ValueError):
                    exact_banded_forrelation(p,g,max_bandwidth=5)

    def test_sign_flip_and_refusals(self):
        p,g0=make_pair(2)
        _,gm=make_pair(2,sign_flip=True)
        self.assertEqual(independent_walsh_sum(p,gm),-(1<<12))
        self.assertEqual(classify_explicit_pair(2,p,gm).decision,"YES")
        self.assertEqual(classify_explicit_pair(2,p,gm).signed_forrelation,-1)
        _,g1=make_pair(2,tilt=1,sign_flip=True)
        self.assertEqual(classify_explicit_pair(2,p,g1).decision,"NO")
        tampered_p=CubicPhase(8,p.monomials+(1,))
        self.assertEqual(classify_explicit_pair(2,tampered_p,g0).decision,"OUTSIDE_PROMISE")
        missing=CubicPhase(8,tuple(m for m in g0.monomials if m!=g0.monomials[0]))
        self.assertEqual(classify_explicit_pair(2,p,missing).decision,"OUTSIDE_PROMISE")
        with self.assertRaises(ValueError):
            make_pair(1)
        with self.assertRaises(ValueError):
            make_pair(2,tilt=1<<8)

    def test_public_dual_sampling_general_cubic_g(self):
        rng=random.Random(4102026)
        for r in (2,3):
            n=4*r
            p,dual=make_pair(r)
            masks=[mask for mask in range(1<<n) if mask.bit_count()<=3]
            for _ in range(8 if r==2 else 2):
                g=CubicPhase(n,tuple(mask for mask in masks if rng.randrange(8)==0))
                avg=public_dual_sample_mean(r,g.evaluate,tuple(range(1<<n)))
                direct=Fraction(independent_walsh_sum(p,g),1<<(3*n//2))
                self.assertEqual(avg,direct)
            self.assertEqual(public_dual_sample_mean(r,dual.evaluate,
                             tuple(range(1<<n))),1)
            _,no=make_pair(r,tilt=1)
            self.assertEqual(public_dual_sample_mean(r,no.evaluate,
                             tuple(range(1<<n))),0)

    def test_three_query_classical_oracle_no_advantage(self):
        rng=random.Random(261111204)
        r=2
        N=1<<(4*r)
        for tilt in range(N):
            _,g=make_pair(r,tilt=tilt,sign_flip=(tilt%2==0))
            count=sum(((y&tilt).bit_count()&1)==0 for y in range(N))
            self.assertEqual(count,N if tilt==0 else N//2)
            for _ in range(5):
                y1,y2=rng.randrange(N),rng.randrange(N)
                got=three_query_classical_tilt_test(r,g.evaluate,y1,y2)
                expected=("NO" if ((y1&tilt).bit_count()&1) or
                          ((y2&tilt).bit_count()&1) else "YES")
                self.assertEqual(got,expected)
        self.assertEqual(Fraction((N//2)**2,N*N),Fraction(1,4))
        with self.assertRaises(ValueError):
            three_query_classical_tilt_test(2,lambda y:0,-1,3)

    def test_simultaneous_permutation_is_invariant(self):
        rng=random.Random(12345)
        p,g=make_pair(2)
        for _ in range(12):
            order=list(range(8))
            rng.shuffle(order)
            self.assertEqual(independent_walsh_sum(
                relabel_phase(p,tuple(order)),relabel_phase(g,tuple(order))),1<<12)


if __name__=="__main__":
    unittest.main()
