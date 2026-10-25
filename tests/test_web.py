"""Real loopback HTTP integration tests for the PHYSQED-Q workbench."""

import http.client
import json
from pathlib import Path
import threading
import unittest

from physqed_q.web import make_server


EXAMPLE = json.loads(
    (Path(__file__).resolve().parents[1] / "examples" / "optimize.json").read_text()
)


class WorkbenchHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server(port=0, lean_executable="/no/such/lean")
        cls.port = cls.server.server_port
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def request(self, method, path, data=None, *, headers=None, raw=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=8)
        defaults = {"Host": f"127.0.0.1:{self.port}",
                    "Origin": f"http://127.0.0.1:{self.port}",
                    "Content-Type": "application/json"}
        if headers:
            defaults.update(headers)
        body = raw if raw is not None else (
            json.dumps(data).encode("utf-8") if data is not None else None
        )
        conn.request(method, path, body=body, headers=defaults)
        response = conn.getresponse()
        payload = response.read()
        result = response.status, dict(response.getheaders()), payload
        conn.close()
        return result

    def test_optimizes_and_independently_verifies_exact_example(self):
        status, headers, body = self.request(
            "POST", "/api/compile", {"circuit": EXAMPLE}
        )
        self.assertEqual(status, 200)
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(headers["Cache-Control"], "no-store")
        data = json.loads(body)
        self.assertTrue(data["verification"]["verified"])
        self.assertEqual(len(data["receipt"]["input"]["gates"]), 7)
        self.assertEqual(len(data["receipt"]["optimized"]["gates"]), 2)
        self.assertEqual(data["receipt"]["metrics"]["input"]["t_gates"], 2)
        self.assertEqual(data["receipt"]["metrics"]["optimized"]["t_gates"], 0)
        self.assertFalse(data["verification"]["lean_kernel_verified"])

        status, _, body = self.request(
            "POST", "/api/verify", {"receipt": data["receipt"]}
        )
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(body)["verification"]["verified"])

    def test_tampered_receipt_does_not_receive_success(self):
        _, _, body = self.request("POST", "/api/compile", {"circuit": EXAMPLE})
        receipt = json.loads(body)["receipt"]
        receipt["optimized"]["gates"] = []
        status, _, result = self.request("POST", "/api/verify", {"receipt": receipt})
        self.assertEqual(status, 422)
        self.assertFalse(json.loads(result)["ok"])

    def test_examples_are_real_repo_files(self):
        status, _, body = self.request("GET", "/api/examples/optimize")
        self.assertEqual(status, 200)
        self.assertEqual(len(json.loads(body)["circuit"]["gates"]), 7)
        for name in ("bell", "ghz"):
            with self.subTest(name=name):
                status, _, body = self.request("GET", "/api/examples/" + name)
                self.assertEqual(status, 200)
                self.assertGreater(len(json.loads(body)["circuit"]["gates"]), 0)

    def test_visual_editor_assets_are_served_from_local_package(self):
        for path, content_type, signature in (
            ("/", "text/html", b"PHYSQED-Q"),
            ("/app.js", "text/javascript", b"fetch("),
            ("/styles.css", "text/css", b".circuit-grid"),
        ):
            with self.subTest(path=path):
                status, headers, body = self.request("GET", path)
                self.assertEqual(status, 200)
                self.assertIn(content_type, headers["Content-Type"])
                self.assertIn(signature, body)
                self.assertIn("default-src 'self'", headers["Content-Security-Policy"])
                self.assertEqual(headers["X-Frame-Options"], "DENY")

    def test_rejects_duplicate_keys_and_nonfinite_numbers(self):
        for raw in (b'{"circuit":{},"circuit":{}}',
                    b'{"circuit":{"qubits":NaN}}', b"not json"):
            with self.subTest(raw=raw):
                status, _, body = self.request("POST", "/api/compile", raw=raw)
                self.assertEqual(status, 400)
                self.assertFalse(json.loads(body)["ok"])

    def test_rejects_bad_shapes_and_content_types(self):
        status, _, _ = self.request("POST", "/api/compile", {"circuit": EXAMPLE, "extra": 1})
        self.assertEqual(status, 400)
        status, _, _ = self.request("POST", "/api/compile", {"circuit": EXAMPLE},
                                    headers={"Content-Type": "text/plain"})
        self.assertEqual(status, 415)

    def test_rejects_oversize_body(self):
        status, headers, body = self.request("POST", "/api/compile", raw=b"x" * (256 * 1024 + 1))
        self.assertEqual(status, 413)
        self.assertEqual(headers.get("Connection"), "close")
        self.assertFalse(json.loads(body)["ok"])

    def test_prevents_host_and_origin_spoofing(self):
        for headers in ({"Host": "attacker.example"},
                        {"Origin": "https://attacker.example"},
                        {"Origin": "null"}):
            with self.subTest(headers=headers):
                status, _, body = self.request(
                    "POST", "/api/compile", {"circuit": EXAMPLE}, headers=headers
                )
                self.assertEqual(status, 403)
                self.assertFalse(json.loads(body)["ok"])

    def test_rejects_path_traversal_and_unknown_routes(self):
        for path in ("/api/examples/../compiler.py", "/physqed_q/kernel.py",
                     "/favicon.ico", "/api/not-real"):
            with self.subTest(path=path):
                status, _, _ = self.request("GET", path)
                self.assertEqual(status, 404)

    def test_missing_lean_executable_fails_closed(self):
        _, _, body = self.request("POST", "/api/compile", {"circuit": EXAMPLE})
        receipt = json.loads(body)["receipt"]
        status, _, body = self.request("POST", "/api/lean", {"receipt": receipt})
        self.assertEqual(status, 422)
        self.assertFalse(json.loads(body)["ok"])


if __name__ == "__main__":
    unittest.main()
