"""Gate 5 numerical and contract tests. No real-hardware claims."""
import unittest
try:
    import numpy as np
    from benchmarks.gate5_matched_readout import (
        readout_channel, simplex_projection, tvd, probs, SHOTS, REPS
    )
except ModuleNotFoundError as exc:
    if exc.name != "numpy":
        raise
    np = None


@unittest.skipIf(np is None, "optional NumPy dependency unavailable")
class MatchedReadoutTests(unittest.TestCase):
    def test_readout_counterfactual_and_inversion(self):
        matrices={"0":[[.9,.1],[.1,.9]],"1":[[.8,.2],[.2,.8]]}
        M=readout_channel(matrices,[0,1])
        p=np.array([.5,0,0,.5],dtype=float)
        y=M@p
        self.assertAlmostEqual(float(y.sum()),1)
        self.assertTrue(np.allclose(np.linalg.solve(M,y),p,atol=1e-12))
        # Swapping the channels changes outcomes for an asymmetric ideal state.
        q=np.array([1,0,0,0],dtype=float)
        self.assertFalse(np.allclose(M@q,readout_channel(matrices,[1,0])@q))
        self.assertAlmostEqual(tvd(q,q),0)
        self.assertAlmostEqual(tvd(np.array([1,0]),np.array([0,1])),1)

    def test_refuse_singular_channel(self):
        matrices={"0":[[.5,.5],[.5,.5]]}
        with self.assertRaises(RuntimeError):
            readout_channel(matrices,[0])

    def test_projection_probability_simplex_and_negative_values(self):
        x=np.array([1.1,-.1,0.])
        out=simplex_projection(x)
        self.assertAlmostEqual(float(out.sum()),1)
        self.assertTrue(np.all(out>=0))
        self.assertTrue(np.allclose(out,[1.,0.,0.]))
        already=np.array([.2,.8,0.])
        self.assertTrue(np.allclose(simplex_projection(already),already))

    def test_fixed_evidence_and_bounded_sampling_contract(self):
        self.assertEqual(SHOTS,(8192,65536))
        self.assertEqual(REPS,50)
        self.assertEqual(len(probs({"00":.5,"11":.5},2)),4)
        with self.assertRaises(RuntimeError):
            probs({"00":.7},2)


if __name__=="__main__":
    unittest.main()
