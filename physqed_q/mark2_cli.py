"""Public PHYSQED-Q Mark II command; stable compatibility adapter.

Use 'python -m physqed_q.mark2_cli'. Internal files with the historical
vnext_* prefix are implementation IDs, never the product name.
"""
from .vnext_mark2_cli import main

if __name__ == "__main__":
    raise SystemExit(main())
