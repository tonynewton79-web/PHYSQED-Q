"""Public PHYSQED-Q Gate 8 command. Backwards-compatible legacy CLI wrapper.

Use 'python -m physqed_q.gate8_cli'. The historical vnext_cli module
remains solely for compatibility with archived verification receipts.
"""
from .vnext_cli import main

if __name__ == "__main__":
    raise SystemExit(main())
