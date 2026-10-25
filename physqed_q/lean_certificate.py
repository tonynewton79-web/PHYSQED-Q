"""Fail-closed, bounded receipt-to-Lean full-operator certificate bridge.

The generated theorem is checked by a real Lean 4.24.0 kernel. The bridge
itself, its translation, and the Python interpreter are NOT Lean-formalized.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from .compiler import CertificateError, verify_receipt


MAX_LEAN_GATES = 16
MAX_JSON_BYTES = 256 * 1024
LEAN_VERSION = "4.24.0"
REPORT_SCHEMA = "physqed-q-lean-theorem-attestation-v1"
FORMAL_DIR = Path(__file__).resolve().parent.parent / "formal"
SINGLE_GATE = {"H": "h", "X": "x", "Z": "z", "S": "s",
               "SDG": "sdg", "T": "t", "TDG": "tdg"}


class LeanBridgeError(ValueError):
    """Refused a receipt or a missing/failed Lean check."""


def _gate_constructor(gate):
    kind, targets = gate["gate"], tuple(gate["qubits"])
    if kind in SINGLE_GATE:
        return "." + SINGLE_GATE[kind] + str(targets[0])
    if kind == "CNOT":
        return ".cnot01" if targets == (0, 1) else ".cnot10"
    if kind == "CZ":
        return ".cz"
    if kind == "SWAP":
        return ".swap"
    raise LeanBridgeError("unexpected gate after receipt validation")


def _lean_word(gates):
    return "[" + ", ".join(_gate_constructor(gate) for gate in gates) + "]"


def render_receipt_theorem(receipt):
    """Deterministically compile validated circuit *data* into a Lean theorem.

    The user-supplied circuit name never appears in generated Lean text.
    The named receipt digest appears only in a non-authoritative comment;
    the full explicit gate words are what Lean actually checks.
    """
    try:
        verify_receipt(receipt)
    except (CertificateError, TypeError, RecursionError) as exc:
        raise LeanBridgeError("invalid source receipt") from exc
    source, target = receipt["input"], receipt["optimized"]
    if source["qubits"] != 2:
        raise LeanBridgeError("Lean receipt bridge currently supports exactly two qubits")
    if len(source["gates"]) > MAX_LEAN_GATES or len(target["gates"]) > MAX_LEAN_GATES:
        raise LeanBridgeError("Lean receipt bridge has a limit of sixteen gates")
    first, second = _lean_word(source["gates"]), _lean_word(target["gates"])
    return (
        "import TwoQubitSemantics\n\n"
        "set_option maxRecDepth 10000\n"
        "set_option maxHeartbeats 0\n\n"
        "open PHYSQEDQ\n\n"
        f"-- Untrusted receipt integrity reference: {receipt['receipt_sha256']}\n"
        f"def receiptInput : List QGate := {first}\n"
        f"def receiptOutput : List QGate := {second}\n\n"
        "theorem receiptFullOperatorEquality :\n"
        "    operatorEq (operator receiptInput) (operator receiptOutput) := by\n"
        "  unfold operatorEq stateEq eEq qEq\n"
        "  decide\n"
    )


def _checked_process(command, *, cwd, env, timeout_seconds):
    try:
        result = subprocess.run(command, cwd=cwd, env=env, text=True,
                                capture_output=True, timeout=timeout_seconds,
                                check=False)
    except (OSError, subprocess.TimeoutExpired, UnicodeError) as exc:
        raise LeanBridgeError("Lean executable unavailable or verification timed out") from exc
    if result.returncode != 0:
        detail = (result.stdout + result.stderr)[-2500:].strip()
        raise LeanBridgeError("Lean rejected generated theorem: " + detail)
    return result.stdout.strip()


def _run_source(source, *, lean_executable="lean", timeout_seconds=30):
    """Compile generated source against freshly compiled trusted formal files.

    Private interface used by negative integration tests; it must never be
    exposed as a service accepting arbitrary client-supplied Lean code.
    """
    if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 120:
        raise LeanBridgeError("invalid Lean timeout")
    if not isinstance(lean_executable, str) or not lean_executable:
        raise LeanBridgeError("invalid Lean executable")
    env = os.environ.copy()
    version = _checked_process([lean_executable, "--version"], cwd=FORMAL_DIR,
                               env=env, timeout_seconds=timeout_seconds)
    if not re.match(r"^Lean \(version " + re.escape(LEAN_VERSION) + r"(?:,|\))", version):
        raise LeanBridgeError("expected official Lean 4.24.0 toolchain")

    with tempfile.TemporaryDirectory(prefix="physqed_q_lean_") as directory:
        root = Path(directory)
        before = env.get("LEAN_PATH")
        env["LEAN_PATH"] = str(root) + (os.pathsep + before if before else "")
        for module in ("GateIdentities", "TwoQubitSemantics"):
            _checked_process(
                [lean_executable, "-o", str(root / (module + ".olean")),
                 str(FORMAL_DIR / (module + ".lean"))],
                cwd=FORMAL_DIR, env=env, timeout_seconds=timeout_seconds,
            )
        witness = root / "ReceiptGenerated.lean"
        witness.write_text(source, encoding="utf-8")
        _checked_process([lean_executable, str(witness)], cwd=FORMAL_DIR,
                         env=env, timeout_seconds=timeout_seconds)
    return version


def certify_receipt(receipt, *, lean_executable="lean", timeout_seconds=30):
    """Return an attestation only when the complete generated theorem compiles."""
    source = render_receipt_theorem(receipt)
    version = _run_source(source, lean_executable=lean_executable,
                          timeout_seconds=timeout_seconds)
    return {
        "schema": REPORT_SCHEMA,
        "receipt_sha256": receipt["receipt_sha256"],
        "lean_source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "formal_source_sha256": {
            filename: hashlib.sha256((FORMAL_DIR / filename).read_bytes()).hexdigest()
            for filename in ("GateIdentities.lean", "TwoQubitSemantics.lean")
        },
        "lean_compiler": version,
        "lean_theorem_checked": True,
        "python_receipt_checked": True,
        "python_compiler_end_to_end_formalized": False,
        "kernel_scope": "two-qubit four-column exact operator in explicit Q(sqrt(2),i) Lean model",
        "not_an_authenticity_signature": True,
    }


def _reject_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise LeanBridgeError(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path, help="complete existing receipt JSON")
    parser.add_argument("--lean", default="lean", help="trusted official Lean binary")
    parser.add_argument("--emit-lean", type=Path, help="save compiled theorem source")
    parser.add_argument("--output", type=Path, help="save attestation as JSON")
    args = parser.parse_args(argv)
    try:
        with args.receipt.open("rb") as handle:
            payload = handle.read(MAX_JSON_BYTES + 1)
        if len(payload) > MAX_JSON_BYTES:
            raise LeanBridgeError("receipt exceeds 256 KiB")
        receipt = json.loads(payload.decode("utf-8"), object_pairs_hook=_reject_duplicates)
        report = certify_receipt(receipt, lean_executable=args.lean)
        if args.emit_lean is not None:
            with args.emit_lean.open("x", encoding="utf-8") as handle:
                handle.write(render_receipt_theorem(receipt))
        displayed = json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.output is None:
            sys.stdout.write(displayed)
        else:
            with args.output.open("x", encoding="utf-8") as handle:
                handle.write(displayed)
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        print(f"LEAN CERTIFICATE REJECTED: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
