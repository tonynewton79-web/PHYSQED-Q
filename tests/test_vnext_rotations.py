"""PHYSQED-Q vNext: independent dense matrix, exact rational and security tests."""
from copy import deepcopy
from fractions import Fraction
import random
import unittest

from physqed_q.vnext import (
    VNextError, NATIVE_GATES, compile_vnext, rat, verify_vnext,
    _hash, _nearest_quarter_turn, validate_program, validate_target,
)
from physqed_q.vnext_numeric import check_numeric_bound


def target(n,*,native=False,p1="1/1000",p2="1/100",
           readout=None,edges=None):
    if edges is None:
        edges=[[i,j] for i in range(n) for j in range(i+1,n)]
    names=set(NATIVE_GATES)
    if not native:
        names.remove("RZPI")
    return {"name":"OWN_DECLARED_NO_DEVICE",
            "qubits":n,"native_gates":sorted(names),
            "couplings":edges,
            "one_qubit_fault":p1,
            "two_qubit_fault":p2,
            "readout_faults":readout if readout is not None else ["1/100"]*n,
            "provenance":"synthetic"}


def source(n=2):
    return {"name":"vnext-parametric-independent-test","qubits":n,
            "gates":[
                {"gate":"RZPI","qubits":[0],"angle_pi":"1/3"},
                {"gate":"RXPI","qubits":[1],"angle_pi":"-1/5"},
                {"gate":"RYPI","qubits":[0],"angle_pi":"2/7"},
                {"gate":"CNOT","qubits":[0,1]},
                {"gate":"U3PI","qubits":[1],
                 "angles_pi":["1/4","-1/3","1/6"]},
                {"gate":"CZ","qubits":[0,1]},
                {"gate":"RZPI","qubits":[0],"angle_pi":"-7/4"},
            ]}


class VNextRotationTests(unittest.TestCase):
    def test_native_rational_pi_rotations_are_exact(self):
        receipt=compile_vnext(source(),target(2,native=True),max_error="0")
        self.assertEqual(receipt["projective_operator_bound"],"0")
        self.assertEqual(receipt["rotation_mode"],"exact_native")
        self.assertTrue(any(g["gate"]=="RZPI" for g in receipt["compiled"]["gates"]))
        self.assertTrue(verify_vnext(receipt)["verified"])
        numeric=check_numeric_bound(receipt)
        self.assertLess(numeric["numeric_frobenius_distance"],1e-11)

    def test_finite_clifford_t_projective_bound(self):
        receipt=compile_vnext(source(),target(2,native=False),max_error="1")
        self.assertEqual(receipt["rotation_mode"],"bounded_clifford_t")
        self.assertTrue(verify_vnext(receipt)["verified"])
        self.assertLess(Fraction(receipt["projective_operator_bound"]),1)
        self.assertGreater(Fraction(receipt["projective_operator_bound"]),0)
        self.assertFalse(any(g["gate"]=="RZPI" for g in receipt["compiled"]["gates"]))
        check_numeric_bound(receipt)

    def test_zero_fault_probability_gives_zero_noise_bound(self):
        src={"name":"exact-no-noise","qubits":2,
             "gates":[{"gate":"H","qubits":[0]},
                      {"gate":"CNOT","qubits":[0,1]}]}
        rc=compile_vnext(src,target(2,p1="0",p2="0",
                                    readout=["0","0"]),max_error="0")
        self.assertEqual(rc["projective_operator_bound"],"0")
        self.assertEqual(rc["stochastic_fault_tvd_bound"],"0")
        self.assertEqual(rc["combined_output_tvd_bound"],"0")
        check_numeric_bound(rc)

    def test_exact_no_fault_coupling_product(self):
        src={"name":"noisy","qubits":2,
             "gates":[{"gate":"H","qubits":[0]},
                      {"gate":"CNOT","qubits":[0,1]}]}
        p1=Fraction(1,100)
        p2=Fraction(1,10)
        r0=Fraction(1,20)
        r1=Fraction(1,5)
        rc=compile_vnext(src,target(2,p1=str(p1),p2=str(p2),
                                    readout=[str(r0),str(r1)]),
                         max_error="0")
        expected=1-(1-p1)*(1-p2)*(1-r0)*(1-r1)
        self.assertEqual(Fraction(rc["stochastic_fault_tvd_bound"]),expected)
        self.assertEqual(Fraction(rc["combined_output_tvd_bound"]),expected)

    def test_tight_requested_tolerance_refuses_finite_gate_rounding(self):
        with self.assertRaisesRegex(VNextError,"exceeds tolerance"):
            compile_vnext(source(),target(2,native=False),max_error="1/8")
        with self.assertRaisesRegex(VNextError,"rational"):
            compile_vnext(source(),target(2,native=False),max_error="0.0001")

    def test_half_up_nearest_phase_is_deterministic(self):
        self.assertEqual(_nearest_quarter_turn(Fraction(1,8)),1)
        self.assertEqual(_nearest_quarter_turn(Fraction(-1,8)),0)
        self.assertEqual(_nearest_quarter_turn(Fraction(-3,8)),-1)
        self.assertEqual(_nearest_quarter_turn(Fraction(7,4)),7)

    def test_strict_integer_and_fraction_and_target_shape(self):
        for bad in ("1/0","01/2","2/4","-0","0.125","1e-2","1/1000000000001",
                    "33","-33",None,True,0.5):
            with self.subTest(value=bad):
                with self.assertRaises(VNextError):
                    rat(bad)
        for bad in (1.0,True,"3",0,5,-1):
            raw=source()
            raw["qubits"]=bad
            with self.subTest(qubits=bad):
                with self.assertRaises(VNextError):
                    validate_program(raw)
        bad=target(2)
        bad["native_gates"].append("FAKE_QPU_GATE")
        with self.assertRaises(VNextError):
            validate_target(bad)

    def test_fail_closed_missing_native_and_invalid_connectivity(self):
        bad=target(2,native=True)
        bad["native_gates"].remove("H")
        with self.assertRaisesRegex(VNextError,"lowered gate H"):
            compile_vnext(source(),bad,max_error="1")
        with self.assertRaisesRegex(VNextError,"physical coupling"):
            compile_vnext(source(),target(2,native=True,edges=[]),
                          max_error="1")

    def test_invalid_gate_and_bare_angle_are_refused(self):
        bad=source()
        bad["gates"][0]["angle_pi"]=0.25
        with self.assertRaises(VNextError):
            compile_vnext(bad,target(2),max_error="1")
        bad=source()
        bad["gates"][0]["gate"]="VIBRATION_QPU"
        with self.assertRaises(VNextError):
            compile_vnext(bad,target(2),max_error="1")

    def test_receipt_adversarial_rehash_and_forged_claims(self):
        receipt=compile_vnext(source(),target(2),max_error="1")
        tampered=deepcopy(receipt)
        tampered["projective_operator_bound"]="0"
        with self.assertRaises(VNextError):
            verify_vnext(tampered)
        tampered["receipt_sha256"]=_hash({k:v for k,v in tampered.items()
                                          if k!="receipt_sha256"})
        with self.assertRaisesRegex(VNextError,"claimed operator"):
            verify_vnext(tampered)
        forged=deepcopy(receipt)
        forged["claims"]["verified_quantum_hardware"]=True
        forged["receipt_sha256"]=_hash({k:v for k,v in forged.items()
                                         if k!="receipt_sha256"})
        with self.assertRaises(VNextError):
            verify_vnext(forged)
        tampered=deepcopy(receipt)
        tampered["compiled"]["gates"][0]["gate"]="X"
        tampered["receipt_sha256"]=_hash({k:v for k,v in tampered.items()
                                          if k!="receipt_sha256"})
        with self.assertRaises(VNextError):
            verify_vnext(tampered)

    def test_randomized_exact_and_bounded_2_qubit_matrix_control(self):
        rng=random.Random(20261118)
        angles=["0","1/2","-1/2","1/3","-1/7","-4/5","1/8","-3/8","5/6"]
        for k in range(32):
            circuit={"name":f"rng-{k}","qubits":2,"gates":[]}
            for _ in range(rng.randint(1,8)):
                kind=rng.choice(["RZPI","RXPI","RYPI","U3PI",
                                 "H","X","Z","T","CNOT","CZ"])
                n_q=2 if kind in {"CNOT","CZ"} else 1
                qs=([0,1] if n_q==2 else [rng.randrange(2)])
                g={"gate":kind,"qubits":qs}
                if kind=="U3PI":
                    g["angles_pi"]=[rng.choice(angles) for j in range(3)]
                elif kind in {"RZPI","RXPI","RYPI"}:
                    g["angle_pi"]=rng.choice(angles)
                circuit["gates"].append(g)
            for native in (True,False):
                try:
                    r=compile_vnext(circuit,target(2,native=native),max_error="1")
                except VNextError as exc:
                    # A dense test source with many quarter-turn roundings
                    # can exceed the declared budget: refusal is required.
                    if native or "exceeds tolerance" not in str(exc):
                        raise
                    continue
                self.assertTrue(verify_vnext(r)["verified"])
                check_numeric_bound(r)


if __name__=="__main__":
    unittest.main()
