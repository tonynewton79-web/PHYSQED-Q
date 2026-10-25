"""Dependency-free, loopback-only PHYSQED-Q visual workbench.

Run: python -m physqed_q.web --port 8765
The server delegates all mathematics to the existing exact Python engine.
It is not designed for public-network hosting or multi-user deployment.
"""

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlsplit
import webbrowser

from .compiler import CertificateError, compile_circuit, verify_receipt
from .kernel import CircuitError
from .lean_certificate import LeanBridgeError, certify_receipt


MAX_BODY = 256 * 1024
ASSETS = Path(__file__).resolve().parent / "web_assets"
EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
STATIC_ROUTES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
}
SAMPLES = {"bell", "ghz", "optimize"}


def _no_duplicate_fields(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("nonfinite JSON value")


class WorkbenchHandler(BaseHTTPRequestHandler):
    """Minimal HTTP boundary; no filesystem path is derived from a URL."""

    protocol_version = "HTTP/1.1"
    lean_executable = "lean"

    def log_message(self, _format, *_args):
        # Quiet local server; client-originated strings never become log format.
        return

    def _allowed_host(self):
        hosts = self.headers.get_all("Host", [])
        return (len(hosts) == 1 and hosts[0] in {
            f"127.0.0.1:{self.server.server_port}",
            f"localhost:{self.server.server_port}",
        })

    def _guard_request(self, *, write=False):
        if not self._allowed_host():
            self._json_error(403, "invalid local Host")
            return False
        if write:
            origin = self.headers.get("Origin")
            if origin is not None and origin != "http://" + self.headers["Host"]:
                self._json_error(403, "cross-origin write denied")
                return False
        return True

    def _send(self, code, content, content_type, *, no_store=True):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        if self.close_connection:
            self.send_header("Connection", "close")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy",
                         "default-src 'self'; script-src 'self'; style-src 'self'; "
                         "object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        if no_store:
            self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def _json(self, code, value):
        raw = json.dumps(value, allow_nan=False, sort_keys=True).encode("utf-8")
        self._send(code, raw, "application/json; charset=utf-8")

    def _json_error(self, code, message):
        # A rejected POST may have unread bytes; never reparse them as an HTTP
        # request on a persistent connection.
        self.close_connection = True
        self._json(code, {"ok": False, "error": str(message)})

    def do_GET(self):
        if not self._guard_request():
            return
        path = urlsplit(self.path).path
        if path in STATIC_ROUTES:
            filename, kind = STATIC_ROUTES[path]
            try:
                content = (ASSETS / filename).read_bytes()
            except OSError:
                self._json_error(404, "page not found")
                return
            self._send(200, content, kind)
            return
        if path.startswith("/api/examples/"):
            name = path.removeprefix("/api/examples/")
            if name in SAMPLES:
                try:
                    with (EXAMPLES / (name + ".json")).open("r", encoding="utf-8") as handle:
                        circuit = json.load(handle, object_pairs_hook=_no_duplicate_fields,
                                            parse_constant=_reject_constant)
                    self._json(200, {"circuit": circuit})
                except (OSError, ValueError, RecursionError):
                    self._json_error(500, "example could not be loaded")
                return
        self._json_error(404, "route not found")

    def _read_json_body(self):
        if self.headers.get("Transfer-Encoding") or len(self.headers.get_all("Content-Length", [])) != 1:
            raise _HTTPInputError(400, "expected one Content-Length header")
        media_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if media_type != "application/json":
            raise _HTTPInputError(415, "Content-Type must be application/json")
        try:
            length = int(self.headers["Content-Length"])
        except (TypeError, ValueError):
            raise _HTTPInputError(400, "invalid Content-Length") from None
        if length < 1:
            raise _HTTPInputError(400, "empty JSON request")
        if length > MAX_BODY:
            raise _HTTPInputError(413, "JSON request exceeds 256 KiB")
        self.connection.settimeout(10)
        raw = self.rfile.read(length)
        if len(raw) != length:
            raise _HTTPInputError(400, "incomplete JSON body")
        try:
            data = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicate_fields,
                              parse_constant=_reject_constant)
        except (UnicodeError, ValueError, RecursionError):
            raise _HTTPInputError(400, "invalid or ambiguous JSON") from None
        if type(data) is not dict:
            raise _HTTPInputError(400, "request body must be a JSON object")
        return data

    def do_POST(self):
        if not self._guard_request(write=True):
            return
        path = urlsplit(self.path).path
        if path not in {"/api/compile", "/api/verify", "/api/lean"}:
            self._json_error(404, "route not found")
            return
        try:
            payload = self._read_json_body()
            field = "circuit" if path == "/api/compile" else "receipt"
            if set(payload) != {field}:
                raise _HTTPInputError(400, "expected only the '" + field + "' field")
            if path == "/api/compile":
                receipt = compile_circuit(payload["circuit"])
                result = {"receipt": receipt, "verification": verify_receipt(receipt)}
            elif path == "/api/verify":
                result = {"verification": verify_receipt(payload["receipt"])}
            else:
                result = {"attestation": certify_receipt(
                    payload["receipt"], lean_executable=self.lean_executable,
                )}
            self._json(200, result)
        except _HTTPInputError as exc:
            self._json_error(exc.code, exc)
        except (CircuitError, CertificateError, LeanBridgeError, ValueError,
                TypeError, AttributeError, KeyError, IndexError, RecursionError) as exc:
            self._json_error(422, exc)
        except (OSError, TimeoutError):
            self._json_error(503, "local verification service unavailable")


class _HTTPInputError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def make_server(*, port=8765, lean_executable="lean"):
    """Create an IPv4 loopback-only HTTP server; port=0 selects a free port."""
    if type(port) is not int or not 0 <= port <= 65535:
        raise ValueError("port must be an integer from 0 to 65535")
    if not isinstance(lean_executable, str) or not lean_executable:
        raise ValueError("Lean executable must be a nonempty path or command")

    class BoundWorkbenchHandler(WorkbenchHandler):
        pass

    BoundWorkbenchHandler.lean_executable = lean_executable
    return ThreadingHTTPServer(("127.0.0.1", port), BoundWorkbenchHandler)


def main(argv=None):
    parser = argparse.ArgumentParser(description="PHYSQED-Q exact local quantum workbench")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--lean", default="lean", help="optional Lean 4.24.0 executable")
    parser.add_argument("--open", action="store_true", help="open your default browser")
    args = parser.parse_args(argv)
    try:
        with make_server(port=args.port, lean_executable=args.lean) as server:
            url = f"http://127.0.0.1:{server.server_port}/"
            print(f"PHYSQED-Q v0.5 visual workbench: {url}", flush=True)
            print("Local-only; press Ctrl+C to stop.", flush=True)
            if args.open:
                webbrowser.open(url)
            server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        print("PHYSQED-Q stopped.")
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Could not start PHYSQED-Q: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
