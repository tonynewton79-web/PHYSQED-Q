"""Dependency-free vNext QASM source semantics, no external quantum stack."""
import unittest
from physqed_q.vnext import VNextError, compile_vnext,NATIVE_GATES
from physqed_q.vnext_numeric import check_numeric_bound
from physqed_q.vnext_qasm import strict_import,fractional_pi
from physqed_q.pi_interval import PI_LOWER,PI_UPPER,approximate_decimal_radians_as_pi


def qasm(body, registers="qreg q[3];\ncreg c[3];"):
    return 'OPENQASM 2.0;\ninclude "qelib1.inc";\n'+registers+"\n"+body


def target(n):
    return {"name":"OWN_DEVICE_INDEPENDENT_TEST_TARGET",
            "qubits":n,"native_gates":sorted(NATIVE_GATES),
            "couplings":[[i,j] for i in range(n) for j in range(i+1,n)],
            "one_qubit_fault":"0","two_qubit_fault":"0",
            "readout_faults":["0"]*n,"provenance":"synthetic"}


class ExternalQASMTests(unittest.TestCase):
    def test_rational_pi_decimal_is_exact_not_floating(self):
        # Check exact decimal-pi parsing against Fraction independently.
        from fractions import Fraction
        self.assertEqual(fractional_pi("pi*1.79986"),
                         str(Fraction("1.79986")))
        self.assertEqual(fractional_pi("pi*-3.59973"),
                         str(Fraction("-3.59973")))
        self.assertEqual(fractional_pi("pi*0.0564006755"),
                         str(Fraction("0.0564006755")))
        self.assertEqual(fractional_pi("pi"),"1")
        self.assertEqual(fractional_pi("-pi"),"-1")
        self.assertEqual(fractional_pi("0"),"0")
        q=Fraction(fractional_pi("1.5707963267948966"))
        theta=Fraction("1.5707963267948966")
        self.assertLessEqual(
            max(abs(theta-q*PI_LOWER),abs(theta-q*PI_UPPER)),
            Fraction(1,10000000000))
        with self.assertRaises(VNextError):
            fractional_pi("1.2j")
        with self.assertRaises(VNextError):
            fractional_pi("pi*1e20")

    def test_u3_and_rotations_are_operator_equivalent(self):
        text=qasm("""h q[0];
u3(pi*0.5,pi*1.5,pi*0.0564006755) q[1];
rx(pi*-0.5) q[2];
rz(pi*0.25) q[0];
ry(pi*0.12) q[1];
cx q[0],q[1];
measure q[0]->c[0];
measure q[1]->c[1];
measure q[2]->c[2];""")
        imported=strict_import(text,name="external-angle-test")
        self.assertEqual(imported["classical_output_bit_to_quantum_qubit"],
                         [0,1,2])
        receipt=compile_vnext(imported["program"],target(3),max_error="0")
        self.assertEqual(receipt["projective_operator_bound"],"0")
        check_numeric_bound(receipt)

    def test_distinct_register_readout_mapping_and_safe_deferral(self):
        text=qasm("""h q[0];
cx q[0],q[2];
rz(pi*1.79986) q[2];
measure q[2]->m2[0];
rx(pi*0.545344) q[1];
measure q[0]->m0[0];
measure q[1]->m1[0];""",
                  registers="qreg q[3];\ncreg m2[1];\ncreg m0[1];\ncreg m1[1];")
        info=strict_import(text,name="qaoa-like")
        self.assertEqual(info["classical_output_bit_to_quantum_qubit"],
                         [2,0,1])
        self.assertEqual(info["deferred_safe_disjoint_postmeasure_unitaries"],1)
        check_numeric_bound(compile_vnext(info["program"],target(3),
                                          max_error="0"))

    def test_reject_gate_on_measured_qubit(self):
        with self.assertRaisesRegex(VNextError,"MEASURED_QUBIT_USED_AGAIN"):
            strict_import(qasm("""measure q[0]->c[0];
h q[0]; measure q[1]->c[1]; measure q[2]->c[2];"""))
        with self.assertRaisesRegex(VNextError,"DYNAMIC_CONTROL_OR_RESET"):
            strict_import(qasm("""h q[0];
measure q[0]->c[0]; if(c==1) x q[1];
measure q[1]->c[1]; measure q[2]->c[2];"""))
        with self.assertRaisesRegex(VNextError,"DYNAMIC_CONTROL_OR_RESET"):
            strict_import(qasm("""reset q[0];
measure q[0]->c[0]; measure q[1]->c[1]; measure q[2]->c[2];"""))

    def test_bare_decimal_radians_produce_rigorous_error_receipt(self):
        data=qasm("""u3(-0.58,0,0) q[2];
measure q[0]->c[0]; measure q[1]->c[1]; measure q[2]->c[2];""")
        imported=strict_import(data)
        self.assertEqual(len(imported["decimal_radian_witnesses"]),1)
        from fractions import Fraction
        self.assertGreater(Fraction(
            imported["source_to_rationalpi_projective_bound"]),0)
        self.assertLess(Fraction(
            imported["source_to_rationalpi_projective_bound"]),
            Fraction(1,1000000000))
        check_numeric_bound(compile_vnext(imported["program"],target(3),
                                          max_error="0"))

    def test_exact_rational_machin_pi_bounds(self):
        self.assertLess(PI_LOWER,PI_UPPER)
        self.assertGreater(PI_LOWER,Fraction(314159265358979,10**14))
        self.assertLess(PI_UPPER,Fraction(22,7))
        q,e=approximate_decimal_radians_as_pi(Fraction("1.5707963267948966"))
        self.assertGreaterEqual(e,abs(Fraction("1.5707963267948966")-q*PI_LOWER))
        self.assertGreaterEqual(e,abs(Fraction("1.5707963267948966")-q*PI_UPPER))
        self.assertLess(e,Fraction(1,10000000000))

    def test_refuse_unsupported_qasm(self):
        bad=qasm("""cu1(pi/2) q[0],q[1];
measure q[0]->c[0]; measure q[1]->c[1]; measure q[2]->c[2];""")
        with self.assertRaisesRegex(VNextError,"UNSUPPORTED_QASM_GATE:cu1"):
            strict_import(bad)

    def test_duplicate_and_bad_register_rejected(self):
        with self.assertRaisesRegex(VNextError,"DUPLICATE_REGISTER"):
            strict_import(qasm("h q[0];",registers=
                 "qreg q[3];\nqreg q[1];\ncreg c[3];"))
        with self.assertRaisesRegex(VNextError,"QASM_NONFULL_MEASUREMENT"):
            strict_import(qasm("""measure q[0]->c[0];
measure q[1]->c[1];"""))
        with self.assertRaisesRegex(VNextError,"QASM_WIDTH_OUT_OF_SCOPE"):
            strict_import(qasm("h q[0];",registers=
                 "qreg q[3];\nqreg extra[2];\ncreg c[3];"))


if __name__=="__main__":
    unittest.main()
