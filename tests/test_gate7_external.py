"""No cherry-picking: frozen third-party source hashes and strict scope."""
import hashlib
import unittest
from benchmarks.gate7_qasmbench import (
    SOURCE_BLOBS, COMMIT, EXPECTED_N, git_blob_sha, inspect, path_for,
    raw_url, SUPPORTED,
)


class Gate7ExternalSourceTests(unittest.TestCase):
    def test_pnnl_source_revision_and_full_file_manifest(self):
        self.assertEqual(len(SOURCE_BLOBS),EXPECTED_N)
        self.assertEqual(EXPECTED_N,19)
        self.assertEqual(len(dict(SOURCE_BLOBS)),19)
        self.assertEqual(len(COMMIT),40)
        self.assertTrue(all(len(sha)==40 for _,sha in SOURCE_BLOBS))
        self.assertIn(("adder_n4","895cf110c11cc822c7db74110336f88159ca3298"),
                      SOURCE_BLOBS)
        for name,sha in SOURCE_BLOBS:
            self.assertTrue(path_for(name).endswith("/"+name+".qasm"))
            self.assertIn(COMMIT,raw_url(name))
            self.assertTrue(raw_url(name).startswith(
                "https://raw.githubusercontent.com/pnnl/QASMBench/"))
        with self.assertRaises(ValueError):
            path_for("../other")
        self.assertEqual(len(SUPPORTED),10)

    def test_frozen_git_content_addressing_detects_mutations(self):
        data=b"OPENQASM 2.0;\n"
        good=hashlib.sha1(b"blob "+str(len(data)).encode()+b"\x00"+data).hexdigest()
        self.assertEqual(git_blob_sha(data),good)
        self.assertNotEqual(git_blob_sha(data),git_blob_sha(data+b"x"))

    def test_strict_admission_and_unmodified_gate_order(self):
        try:
            from qiskit import qasm2
        except ModuleNotFoundError as exc:
            if exc.name!="qiskit":raise
            self.skipTest("optional qiskit not in minimal core test CI")
        pre='OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg a[2];\ncreg c[2];\n'
        post='measure a[0]->c[0];\nmeasure a[1]->c[1];\n'
        ok=inspect("test",pre+'h a[0];\ncx a[0],a[1];\n'+post,qasm2)
        self.assertTrue(ok["admitted"])
        self.assertEqual(ok["logical"]["gates"],
                         [{"gate":"H","qubits":[0]},
                          {"gate":"CNOT","qubits":[0,1]}])
        unsupported=inspect(
            "test",pre+'rx(pi/3) a[0];\n'+post,qasm2)
        self.assertFalse(unsupported["admitted"])
        self.assertIn("UNSUPPORTED_GATE:rx",unsupported.get("refusals",{}))
        mid=inspect("test",pre+'measure a[0]->c[0];\nh a[1];\n'
                    'measure a[1]->c[1];\n',qasm2)
        self.assertFalse(mid["admitted"])
        self.assertIn("MIDCIRCUIT_MEASUREMENT",mid.get("refusals",{}))
        reordered=inspect("test",pre+'h a[0];\n'
                          'measure a[1]->c[0];\n'
                          'measure a[0]->c[1];\n',qasm2)
        self.assertFalse(reordered["admitted"])
        self.assertIn("OUTPUT_CLASSICAL_ORDER_NOT_IDENTITY",
                      reordered.get("refusals",{}))


if __name__=="__main__":
    unittest.main()
