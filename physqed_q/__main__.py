"""Dependency-free command-line interface for compilation and replay."""

import argparse
import json
from pathlib import Path
import sys

from .compiler import CertificateError, compile_circuit, verify_receipt
from .kernel import CircuitError, evolve, validate_circuit, ZERO


MAX_JSON_BYTES = 262144


def _unique_pairs(pairs):
    data = {}
    for key, value in pairs:
        if key in data:
            raise ValueError(f"repeated JSON key: {key}")
        data[key] = value
    return data


def _load(path):
    with Path(path).open("rb") as stream:
        raw = stream.read(MAX_JSON_BYTES + 1)
    if len(raw) > MAX_JSON_BYTES:
        raise ValueError("JSON input exceeds 256 KiB")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(f"invalid constant {x}")))


def _print_json(value):
    print(json.dumps(value, sort_keys=True, indent=2, allow_nan=False))


def _demo(which):
    base = Path(__file__).resolve().parents[1] / "examples"
    source = validate_circuit(_load(base / f"{which}.json"))
    state = evolve(source)
    width = source["qubits"]
    support = {
        format(i, f"0{width}b"): list(a.coefficients())
        for i, a in enumerate(state) if a != ZERO
    }
    return {"name": source["name"], "qubits": width,
            "basis_amplitudes": support, "lean_kernel_verified": False,
            "hardware_verified": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description="PHYSQED-Q exact bounded circuit compiler")
    sub = parser.add_subparsers(dest="command", required=True)
    compiler = sub.add_parser("compile", help="compile JSON circuit and generate exact certificate")
    compiler.add_argument("input", help="input circuit JSON")
    compiler.add_argument("--output", help="optional path for JSON receipt")
    verifier = sub.add_parser("verify", help="independently replay a JSON receipt")
    verifier.add_argument("receipt", help="receipt file")
    demonstration = sub.add_parser("demo", help="exact Bell/GHZ state amplitudes")
    demonstration.add_argument("which", choices=["bell", "ghz"])
    args = parser.parse_args(argv)
    try:
        if args.command == "compile":
            receipt = compile_circuit(_load(args.input))
            if args.output:
                Path(args.output).write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n",
                                             encoding="utf-8")
                _print_json({"written": str(args.output), "receipt_sha256": receipt["receipt_sha256"],
                             "equivalence_verified": True})
            else:
                _print_json(receipt)
        elif args.command == "verify":
            _print_json(verify_receipt(_load(args.receipt)))
        else:
            _print_json(_demo(args.which))
    except (CircuitError, CertificateError, ValueError, OSError, UnicodeError, RecursionError) as exc:
        print(f"REJECTED: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
