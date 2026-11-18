"""Prespecified deterministic circuit corpus for external benchmark comparison.

DEV and HELDOUT seeds are disjoint. No external optimizer result feeds
generation, and generated circuits are not training data for PHYSQED-Q.
These are synthetic templates, NOT an independent application distribution.
"""
import hashlib
import json
import random

SEEDS = {"dev": 2026111801, "heldout": 2026111802}
COUNTS = {"dev": 3, "heldout": 10}  # per family: 12 development / 40 held-out
FAMILIES = ("control", "target-negative", "mixed", "phase-heavy")
GATES = ("H", "X", "Z", "S", "SDG", "T", "TDG")


def g(name, *qubits):
    return {"gate": name, "qubits": list(qubits)}


def generate(split="heldout"):
    if split not in SEEDS:
        raise ValueError("split must be dev or heldout")
    rng = random.Random(SEEDS[split])
    rows = []
    for family in FAMILIES:
        for index in range(COUNTS[split]):
            n = 2 + rng.randrange(3)
            c, t = rng.sample(range(n), 2)
            if family == "control":
                # Exact T cancellation must be possible, although external
                # compilers can do the same reduction.
                middle = [g("CNOT", c, t)] * (1 + rng.randrange(3))
                gates = [g("T", c)] + middle + [g("TDG", c)]
                # Noninterfering nontrivial variation outside protected word.
                if rng.randrange(2):
                    gates = [g("H", t)] + gates + [g("X", t)]
            elif family == "target-negative":
                gates = [g("T", t), g("CNOT", c, t), g("TDG", t)]
                if rng.randrange(2):
                    gates = [g("H", c)] + gates + [g("Z", c)]
            elif family == "mixed":
                gates = []
                for _ in range(10 + rng.randrange(7)):
                    if rng.randrange(3) == 0:
                        a, b = rng.sample(range(n), 2)
                        gates.append(g("CNOT", a, b))
                    else:
                        gates.append(g(rng.choice(GATES), rng.randrange(n)))
            else:
                other = rng.choice([q for q in range(n) if q != c])
                gates = [
                    g("T", c), g("CNOT", c, t), g("S", c),
                    g("CNOT", c, other), g("TDG", c),
                    g("TDG", c), g("CZ", c, t), g("T", c),
                ]
                if rng.randrange(2):
                    gates += [g("H", t), g("T", t), g("H", t)]
            rows.append({
                "name": f"{split}-{family}-{index:02d}",
                "family": family,
                "circuit": {"name": f"{split}-{family}-{index:02d}",
                            "qubits": n, "gates": gates},
            })
    return rows


def manifest(split="heldout"):
    rows = generate(split)
    b = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf8")
    return {"split": split, "seed": SEEDS[split], "cases": len(rows),
            "sha256": hashlib.sha256(b).hexdigest(),
            "families": {name: sum(r["family"] == name for r in rows)
                         for name in FAMILIES}}


if __name__ == "__main__":
    print(json.dumps({k: manifest(k) for k in SEEDS}, indent=2, sort_keys=True))
