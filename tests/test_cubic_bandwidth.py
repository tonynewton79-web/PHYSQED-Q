"""Independent exact and adversarial checks for cubic-phase transfer contraction."""
import random
import unittest
from fractions import Fraction
from physqed_q.cubic_bandwidth import (
    CubicPhase, exact_banded_forrelation, independent_walsh_sum,
    consecutive_cubic_chain, relabel_phase, recover_cubic_chain_order,
)


class CubicBandwidthTests(unittest.TestCase):
    def test_exhaustive_one_and_two_bits(self):
        for n in (1,2):
            masks=tuple(range(1<<n))
            for a in range(1<<len(masks)):
                f=CubicPhase(n,tuple(mask for j,mask in enumerate(masks) if (a>>j)&1))
                for b in range(1<<len(masks)):
                    g=CubicPhase(n,tuple(mask for j,mask in enumerate(masks) if (b>>j)&1))
                    out=exact_banded_forrelation(f,g)
                    self.assertEqual(out.signed_sum,independent_walsh_sum(f,g))
                    self.assertLessEqual(out.squared_amplitude,1)

    def test_random_banded_degree_three(self):
        rng=random.Random(26111112)
        for n,reps,w in ((3,80,3),(4,80,3),(5,80,3),(6,70,4),
                         (7,60,4),(8,60,4),(9,40,4),(10,30,5)):
            masks=[0]+[m for m in range(1,1<<n) if m.bit_count()<=3 and
                       m.bit_length()-((m&-m).bit_length()-1)<=w]
            for _ in range(reps):
                f=CubicPhase(n,tuple(m for m in masks if rng.randrange(2)))
                g=CubicPhase(n,tuple(m for m in masks if rng.randrange(2)))
                out=exact_banded_forrelation(f,g)
                self.assertEqual(out.signed_sum,independent_walsh_sum(f,g))
                self.assertEqual(out.squared_amplitude,Fraction(out.signed_sum**2,1<<(3*n)))
                self.assertLessEqual(out.max_active_states,4**(w-1))

    def test_linear_hitting_number_but_small_width(self):
        for n in range(3,14):
            f=consecutive_cubic_chain(n)
            out=exact_banded_forrelation(f,f)
            self.assertEqual(out.bandwidth,3)
            self.assertEqual(out.signed_sum,independent_walsh_sum(f,f))
        for n in (48,96,192):
            f=consecutive_cubic_chain(n)
            out=exact_banded_forrelation(f,f)
            self.assertEqual(out.bandwidth,3)
            self.assertLessEqual(out.max_active_states,16)
            self.assertLessEqual(out.squared_amplitude,1)

    def test_constants_signs(self):
        f=CubicPhase(3,(7,))
        g=CubicPhase(3,(7,))
        p=exact_banded_forrelation(f,g)
        self.assertEqual(exact_banded_forrelation(CubicPhase(3,(0,7)),g).signed_sum,-p.signed_sum)
        self.assertEqual(p.signed_sum,independent_walsh_sum(f,g))
        self.assertEqual(exact_banded_forrelation(CubicPhase(1),CubicPhase(1)).signed_sum,2)

    def test_permuted_hidden_chain(self):
        r=random.Random(20261112)
        for n in (3,4,5,6,8,12,42,96):
            original=consecutive_cubic_chain(n)
            shuffled=list(range(n))
            r.shuffle(shuffled)
            scrambled=relabel_phase(original,tuple(shuffled))
            recovered=recover_cubic_chain_order(scrambled)
            self.assertEqual(relabel_phase(scrambled,recovered).bandwidth(),3)
            self.assertEqual(exact_banded_forrelation(scrambled,scrambled,order=recovered,
                              max_bandwidth=3).signed_sum,
                             exact_banded_forrelation(original,original).signed_sum)
            if n<=12:
                self.assertEqual(exact_banded_forrelation(scrambled,scrambled,order=recovered).signed_sum,
                                 independent_walsh_sum(scrambled,scrambled))

    def test_width_gate_and_invalid(self):
        with self.assertRaises(ValueError):
            exact_banded_forrelation(CubicPhase(9,(1|256,)),CubicPhase(9),max_bandwidth=3)
        with self.assertRaises(ValueError):
            CubicPhase(3,(7,7))
        with self.assertRaises(ValueError):
            CubicPhase(4,(15,))
        with self.assertRaises(ValueError):
            CubicPhase(2,(-1,))
        with self.assertRaises(ValueError):
            exact_banded_forrelation(CubicPhase(2),CubicPhase(3))
        with self.assertRaises(ValueError):
            exact_banded_forrelation(CubicPhase(3),CubicPhase(3),order=(0,0,2))
        with self.assertRaises(ValueError):
            recover_cubic_chain_order(CubicPhase(6,(7,14)))
        with self.assertRaises(ValueError):
            independent_walsh_sum(CubicPhase(17),CubicPhase(17))


if __name__=="__main__":
    unittest.main()
