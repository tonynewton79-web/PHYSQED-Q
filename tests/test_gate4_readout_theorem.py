"""Exact rational identity behind Gate 4 readout-only ordering.

For p(x2 x1 x0) = 1[x2=0]/4 (uniform low two bits) and independent
BINARY-SYMMETRIC readout channels on the three measured physical qubits,
TVD(observed, ideal) = error probability of the physical qubit assigned
to logical/classical bit x2. This is elementary prior art, not novelty.

Gate 4's *particular* FakeManilaV2/FakeLagosV2 historical readout
matrices are symmetric, so this identity identifies the full readout-
only contrast without a simulator. It does not apply to asymmetric,
correlated, or context-dependent readout without modification.
"""
from fractions import Fraction
import unittest


def ideal():
    return {i: (Fraction(1, 4) if i < 4 else Fraction(0)) for i in range(8)}


def apply_symmetric_errors(p, errors_per_classical_bit):
    out = {i:Fraction(0) for i in range(8)}
    if len(errors_per_classical_bit) != 3:
        raise ValueError("three logical/classical bits required")
    for true, probability in p.items():
        for observed in range(8):
            weight=probability
            for c,e in enumerate(errors_per_classical_bit):
                if not Fraction(0) <= e <= Fraction(1):
                    raise ValueError("invalid bit-flip channel parameter")
                weight *= e if bool((true>>c)&1) != bool((observed>>c)&1) else 1-e
            out[observed]+=weight
    return out


def tvd_exact(a,b):
    return sum((abs(a[i]-b[i]) for i in range(8)),Fraction(0))/2


class ReadoutIdentityTests(unittest.TestCase):
    def test_all_rational_symmetry_cases(self):
        p=ideal()
        lower=(Fraction(0),Fraction(1,100),Fraction(1,5),Fraction(1,2))
        upper=(Fraction(0),Fraction(219,10000),Fraction(964,10000),
               Fraction(1362,10000),Fraction(4638,10000))
        for e0 in lower:
            for e1 in lower:
                for e2 in upper:
                    with self.subTest(e0=e0,e1=e1,e2=e2):
                        out=apply_symmetric_errors(p,(e0,e1,e2))
                        self.assertEqual(tvd_exact(out,p),e2)
                        self.assertEqual(sum(out.values()),Fraction(1))

    def test_historical_readout_only_contrasts_are_exact(self):
        # For the physical output mapping, classical bit 2 uses:
        # PHYSQED = q1; PyZX = q2. Fractions are from historical
        # archived readout matrices (not live calibrations).
        for phys_e,pyzx_e,expected in (
            (Fraction(219,10000),Fraction(964,10000),Fraction(-745,10000)),
            (Fraction(1362,10000),Fraction(4638,10000),Fraction(-3276,10000)),
        ):
            self.assertEqual(phys_e-pyzx_e,expected)
            self.assertEqual(
                tvd_exact(apply_symmetric_errors(
                    ideal(),(Fraction(1,20),Fraction(1,20),phys_e)),ideal())
                - tvd_exact(apply_symmetric_errors(
                    ideal(),(Fraction(1,20),Fraction(1,20),pyzx_e)),ideal()),
                expected)

    def test_readout_identity_not_claimed_for_asymmetric_channels(self):
        # If the low bits are no longer bistochastic, uniformity is not
        # preserved, so the simple x2-only TVD argument need not hold.
        p=ideal()
        out={i:Fraction(0) for i in range(8)}
        for true,mass in p.items():
            # Force x0=0, which is a valid but asymmetric readout map.
            out[true & ~1]+=mass
        self.assertEqual(tvd_exact(out,p),Fraction(1,2))
        self.assertNotEqual(tvd_exact(out,p),Fraction(0))


if __name__=="__main__":
    unittest.main()
