"""Exact unit tests for the white-box / path-sampling distinction."""
import random
import unittest
from fractions import Fraction

from physqed_q.cubic_bandwidth import independent_walsh_sum
from physqed_q.dense_bent import make_pair
from physqed_q.hccz_circuit import exact_run
from physqed_q.path_sampling_gate import (
    certify_dense_pair, hccz_forrelation_program,
    path_importance_second_moment, exact_sign_only_chi_squared,
    iid_importance_mean_mse_lower_bound, classical_certificate_shortcut,
    phase_to_hccz_gates,
)


class PathSamplingGateTests(unittest.TestCase):
    def test_all_256_eight_bit_tilts(self):
        for t in range(1<<8):
            c=certify_dense_pair(2,tilt=t)
            self.assertEqual(c.classical_decision,'YES' if t==0 else 'NO')
            self.assertEqual(c.path_sign_mean,Fraction(1,16) if t==0 else 0)
            self.assertEqual(c.minimum_single_path_variance,255 if t==0 else 256)
            self.assertEqual(classical_certificate_shortcut(2,t),c.classical_decision)

    def test_exact_fourier_walsh_8_and_12(self):
        rng=random.Random(2026111206)
        for r,tilts in ((2,list(range(256))),(3,[0,1,2,3,7,32,1024]+[rng.randrange(1<<12) for _ in range(24)])):
            n=4*r
            for tilt in tilts:
                p,g=make_pair(r,tilt=tilt)
                S=independent_walsh_sum(p,g)
                self.assertEqual(S,certify_dense_pair(r,tilt=tilt).forrelation_numerator)
                self.assertEqual(Fraction(S,1<<(2*n)),certify_dense_pair(r,tilt=tilt).path_sign_mean)

    def test_full_hccz_state_promise(self):
        # Exact dense state only for r=2: n=8 data and 2 basis-|1> ancillas.
        for tilt,flip in ((0,False),(1,False),(2,False),(3,True),(7,False),(255,True)):
            nq,basis,program,global_sign=hccz_forrelation_program(2,tilt=tilt,sign_flip=flip)
            self.assertEqual(nq,10)
            self.assertEqual(global_sign,-1 if flip else 1)
            self.assertEqual(sum(g.kind=='H' for g in program),24)
            self.assertTrue(all(g.kind in ('H','CCZ') for g in program))
            out=exact_run(nq,program,basis=basis,output=0)
            target=basis|tilt
            self.assertEqual(out.hadamards,24)
            self.assertEqual(out.state_numerators[target],1<<12)  # constant phase omitted as global sign
            self.assertEqual(global_sign*out.state_numerators[target],global_sign*(1<<12))
            self.assertEqual(sum(z!=0 for z in out.state_numerators),1)

    def test_phase_gate_gadget(self):
        from physqed_q.cubic_bandwidth import CubicPhase
        p=CubicPhase(4,(0,1,3,7))
        gates,s=phase_to_hccz_gates(p,4,5)
        self.assertEqual(s,-1)
        self.assertEqual(len(gates),3)
        for x in range(1<<4):
            parity=0
            for gate in gates:
                if all(((x|(1<<4)|(1<<5))>>i)&1 for i in gate.qubits):
                    parity^=1
            self.assertEqual(parity^1,p.evaluate(x))

    def test_importance_cauchy_sharp_and_nonuniform(self):
        for n in (1,2,3):
            N=1<<(2*n)
            uniform=(Fraction(1,N),)*N
            self.assertEqual(path_importance_second_moment(n,uniform),1<<n)
            q=tuple(Fraction(2,N+1) if k==0 else Fraction(1,N+1) for k in range(N))
            self.assertEqual(sum(q),1)
            self.assertGreater(path_importance_second_moment(n,q),1<<n)

    def test_sign_only_chisquared(self):
        for n in (2,4,8,12,16):
            eps2=Fraction(1,1<<n)
            self.assertEqual(exact_sign_only_chi_squared(n,0),0)
            self.assertEqual(exact_sign_only_chi_squared(n,1),eps2)
            self.assertEqual(exact_sign_only_chi_squared(n,2),2*eps2+eps2**2)
        for m in range(0,40):
            a=exact_sign_only_chi_squared(8,m)
            b=exact_sign_only_chi_squared(8,m+1)
            self.assertGreater(b,a)

    def test_mse_bound_and_refusals(self):
        self.assertEqual(iid_importance_mean_mse_lower_bound(2,tilt=0,samples=3),Fraction(255,3))
        self.assertEqual(iid_importance_mean_mse_lower_bound(2,tilt=1,samples=3),Fraction(256,3))
        for args in ({'r':1},{'r':2,'tilt':-1},{'r':2,'tilt':256}):
            with self.assertRaises(ValueError):
                certify_dense_pair(**args)
        with self.assertRaises(ValueError):
            exact_sign_only_chi_squared(3,4)
        with self.assertRaises(ValueError):
            iid_importance_mean_mse_lower_bound(2,samples=0)
        with self.assertRaises(ValueError):
            path_importance_second_moment(2,[Fraction(1,4)]*4)
        with self.assertRaises(ValueError):
            path_importance_second_moment(1,[Fraction(0),Fraction(1,2),Fraction(1,4),Fraction(1,4)])


if __name__=='__main__':
    unittest.main()
