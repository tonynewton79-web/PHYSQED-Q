"""PHYSQED-Q Attack012 exact HCCZ general-order Fourier measurement regression."""
import unittest
from fractions import Fraction
from math import pi
import numpy as np
import random

from physqed_q.fourier_stage import (
    compile_fourier_measurement,sparse_fourier_measurement_state,
    independent_mixture_probability,required_repeats,
    sample_hidden_eigenphase,factoring_from_order,
    abstract_inverse_qft,simulate_inverse_qft_ir,decode_native_measurement,
)
from physqed_q.certified_phase_decode import (
    rational_pi_interval,certified_unit_circle_grid,
    binary_quadrature_phase,reconstruct_phase_exact,
    recover_order_from_exact_phase,
)


class ExactFourierStageTests(unittest.TestCase):
    def test_exact_rebit_full_hccz_distributions(self):
        for N,a,m,t in ((5,2,1,1),(7,2,1,1),(9,2,2,1),
                        (15,2,2,1),(21,2,2,1),(21,2,3,1),
                        (21,2,2,2),(35,2,1,1)):
            stage=compile_fourier_measurement(N,a,m,t)
            self.assertTrue(all(g.kind in ('H','CCZ') for g in stage.gates))
            self.assertTrue(all(len(set(g.qubits))==len(g.qubits) for g in stage.gates))
            self.assertEqual(stage.rebit_wire,stage.n_wires-1)
            got=sparse_fourier_measurement_state(stage)
            self.assertEqual(sum(got.values()),1)
            for k,p in got.items():
                self.assertAlmostEqual(float(p),independent_mixture_probability(stage,k),places=11)

    def test_exact_native_factoring_15(self):
        stage=compile_fourier_measurement(15,2,5,1)
        got=sparse_fourier_measurement_state(stage)
        factor_weight=Fraction(0)
        for k,p in got.items():
            out=decode_native_measurement(stage,k)
            if out['factors'] is not None:
                self.assertEqual(out['factors'],(3,5))
                self.assertEqual(out['order'],4)
                factor_weight+=p
        self.assertEqual(factor_weight,Fraction(1,2))

    def test_growth_and_clean_wires(self):
        last=0
        for m in (1,2,3,4):
            stage=compile_fourier_measurement(21,2,m,1)
            self.assertEqual(len(stage.x_controls),m)
            self.assertEqual(len(stage.y_controls),m)
            self.assertEqual(len(set(stage.work_wires)),len(stage.work_wires))
            self.assertLess(len(stage.gates),10000*m*m*stage.modulus.bit_length()**3)
            self.assertEqual(stage.initial_basis.bit_count(),2)
            self.assertGreater(len(stage.gates),last)
            last=len(stage.gates)

    def test_certified_pi_grid(self):
        lo,hi=rational_pi_interval()
        self.assertLess(hi-lo,Fraction(1,1<<100))
        grid=certified_unit_circle_grid()
        self.assertEqual(len(grid),64)
        for k,(c,s) in enumerate(grid):
            self.assertLess(abs(c/2**24-np.cos(2*pi*k/64)),2**-22)
            self.assertLess(abs(s/2**24-np.sin(2*pi*k/64)),2**-22)
        self.assertEqual(binary_quadrature_phase([0]*16,[0]*8+[1]*8),0)

    def test_exact_rational_grid_unwrap(self):
        for r in (3,4,5,6,7,8,10,12,15):
            N=max(17,r+2);m=2*N.bit_length()+2
            for ell in range(r):
                xs=[];ys=[]
                for j in range(m):
                    angle=2*pi*(ell*(1<<j)%r)/r
                    reps=4096
                    nx=round(reps*(1+np.cos(angle))/2)
                    ny=round(reps*(1+np.sin(angle))/2)
                    xs.append([0]*nx+[1]*(reps-nx))
                    ys.append([0]*ny+[1]*(reps-ny))
                got=reconstruct_phase_exact(xs,ys)
                truth=Fraction(ell,r)
                circ=min((got-truth)%1,(truth-got)%1)
                self.assertLess(circ,Fraction(1,16*(1<<(m-1))))

    def test_hoeffding_budget_exact(self):
        for m in (1,2,5,10,23,40):
            for delta in (Fraction(1,2),Fraction(1,20),Fraction(1,100000)):
                t=required_repeats(m,delta)
                self.assertEqual(t%128,0)
                k=t//128
                self.assertLessEqual(Fraction(4*m,1<<k),delta)
                if k:self.assertGreater(Fraction(4*m,1<<(k-1)),delta)

    def test_reference_factoring_and_order(self):
        rng=random.Random(20261114012)
        for N,a,r,factors in ((15,2,4,(3,5)),(21,2,6,(3,7)),(35,2,12,(5,7))):
            m=2*N.bit_length()+2
            t=required_repeats(m,Fraction(1,20))
            wins=0
            for _ in range(90):
                hidden,x,y=sample_hidden_eigenphase(N,a,m,t,rng)
                phase=reconstruct_phase_exact(x,y)
                order=recover_order_from_exact_phase(phase,N,a)
                if order==r:
                    self.assertEqual(factoring_from_order(N,a,order),factors)
                    wins+=1
            self.assertGreaterEqual(wins,12)

    def test_abstract_iqft_not_hccz(self):
        for m in range(1,7):
            eps=Fraction(1,100)
            plan=abstract_inverse_qft(m,eps)
            self.assertFalse(plan.exact_hccz_compiler_available)
            self.assertLessEqual(plan.omitted_rotation_upper_bound+
                                 plan.retained_rotation_count*plan.per_retained_rotation_budget,eps)
            actual=simulate_inverse_qft_ir(plan)
            L=1<<m
            expected=np.array([[np.exp(-2j*np.pi*x*y/L)/np.sqrt(L)
                                for y in range(L)] for x in range(L)])
            self.assertLess(np.linalg.norm(actual-expected,2),
                            float(plan.omitted_rotation_upper_bound)+1e-11)

    def test_native_output_reader_and_rejections(self):
        stage=compile_fourier_measurement(15,2,2,1)
        for bits in range(16):
            try:
                out=decode_native_measurement(stage,bits)
                self.assertIsInstance(out['phase'],Fraction)
                if out['order'] is not None:
                    self.assertEqual(pow(2,out['order'],15),1)
            except ValueError as e:
                self.assertIn('ambiguous',str(e))
        with self.assertRaises(ValueError):
            decode_native_measurement(stage,1<<4)

    def test_refusals(self):
        for N,a,m,t in ((15,3,2,1),(15,2,0,1),(15,2,2,0),(True,2,2,1)):
            with self.assertRaises(ValueError):compile_fourier_measurement(N,a,m,t)
        for m,eps in ((0,Fraction(1,2)),(2,Fraction(0)),(2,0.1)):
            with self.assertRaises(ValueError):abstract_inverse_qft(m,eps)
        with self.assertRaises(ValueError):reconstruct_phase_exact([],[])
        with self.assertRaises(ValueError):reconstruct_phase_exact([[0,1]],[[0,1]])
        with self.assertRaises(ValueError):recover_order_from_exact_phase(0.2,15,2)


if __name__=="__main__":
    unittest.main()
