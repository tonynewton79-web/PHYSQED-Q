"""Exact finite Grover-style triangle search over ordered vertex triples.

Model: graph-independent uniform preparation and ideal diffusion, six charged
adjacency oracle calls per coherent triangle phase. Diffusion is an explicitly
declared abstract query-free unitary; no physical gate compilation is claimed.
No O(n)-query graph triangle-finding theorem. No hardware measurement.
"""
from __future__ import annotations

from fractions import Fraction
from itertools import combinations, product
import json

from .adjacency_oracle import (
    MAX_VERTICES, OracleError, digest, graph_normalize, triangle_phase_program,
)

SCHEMA = "physqed-q-ideal-triangle-search-v1"
MAX_ITERATIONS = 12
PHASE_CALL_TAGS = (
    ("compute", "u", "v"),
    ("compute", "v", "w"),
    ("compute", "w", "u"),
    ("uncompute", "w", "u"),
    ("uncompute", "v", "w"),
    ("uncompute", "u", "v"),
)
SCOPE = {
    "model": "ideal query-complexity uniform-triple diffusion (not gate-synthesized)",
    "coherent_query_oracle": "O_A|u,v,b>=|u,v,b XOR A_uv>",
    "input_state": "uniform over all n^3 ordered triples, including repetitions",
    "amplitudes": "integer/rational multiples of 1/sqrt(n^3)",
    "probabilities": "exact rational",
    "implemented_graph_vertices": [3, MAX_VERTICES],
    "max_iterations": MAX_ITERATIONS,
    "gate_implementation_proven": False,
    "quantum_speedup_proven": False,
    "O_n_query_algorithm_proven": False,
    "measurement_hardware_verified": False,
    "lean_kernel_verified": False,
}


def canonical_config(config):
    """Reject noncanonical input and all unnamed, uncharged graph access."""
    if not isinstance(config, dict) or set(config) != {
        "graph", "iterations", "verify_measured_candidate"
    }:
        raise OracleError("search requires graph, iterations, verify_measured_candidate")
    graph = graph_normalize(config["graph"])
    if graph["vertices"] < 3:
        raise OracleError("search needs at least three vertices")
    iterations = config["iterations"]
    verify = config["verify_measured_candidate"]
    if type(iterations) is not int or not 0 <= iterations <= MAX_ITERATIONS:
        raise OracleError("iterations outside bounded exact search scope")
    if type(verify) is not bool:
        raise OracleError("verification flag must be boolean")
    if config["graph"] != graph:
        raise OracleError("graph must have canonical sorted edges")
    return {"graph": graph, "iterations": iterations,
            "verify_measured_candidate": verify}


def _fraction(x):
    if not isinstance(x, Fraction):
        raise OracleError("expected exact rational")
    return str(x.numerator) + "/" + str(x.denominator)


def _independent_truth(graph):
    edges = {tuple(e) for e in graph["edges"]}
    return {
        tuple(t) for t in product(range(graph["vertices"]), repeat=3)
        if len(set(t)) == 3
        and all(tuple(sorted((a,b))) in edges
                for a,b in ((t[0],t[1]), (t[1],t[2]), (t[2],t[0])))
    }


def _ledger(iterations, verify):
    records = []
    for j in range(iterations):
        for role, u, v in PHASE_CALL_TAGS:
            records.append({"query_index": len(records)+1, "iteration": j,
                            "role": role, "left": u, "right": v})
    if verify:
        for u,v in (("u","v"),("v","w"),("w","u")):
            records.append({"query_index":len(records)+1,
                            "iteration":"post_measurement",
                            "role":"candidate_verification",
                            "left":u,"right":v})
    return records


def _independent_two_amplitude(n,marked_count,iterations):
    """Independently derive the two-amplitude invariant subspace."""
    total = n**3
    marked = Fraction(1)
    unmarked = Fraction(1)
    f = Fraction(marked_count,total)
    for _ in range(iterations):
        # Reflected phase: marked -> -marked, then diffuse about the mean.
        mean = f*(-marked) + (1-f)*unmarked
        marked,unmarked = 2*mean + marked, 2*mean - unmarked
    success = f*marked**2
    failure = (1-f)*unmarked**2
    if success+failure != 1:
        raise OracleError("two-amplitude normalization failure")
    return marked,unmarked,success


def certify_search(config):
    """Exact dense-search simulation plus independent 2D analytic replay."""
    c = canonical_config(config)
    g = c["graph"]
    n = g["vertices"]
    triples = list(product(range(n),repeat=3))
    N = len(triples)
    marked = _independent_truth(g)
    marks = [triple in marked for triple in triples]

    # Check charged phase circuit is independently admitted by existing
    # PHYSQED-Q oracle program grammar before accepting any query count.
    phase = triangle_phase_program(n)
    kinds = [o["op"] for o in phase["operations"]]
    if kinds.count("QUERY") != 6 or kinds.count("CCZ") != 1 or len(kinds) != 7:
        raise OracleError("base six-query phase program changed")

    numerators = [Fraction(1)] * N  # actual amplitudes / sqrt(N)
    step_summaries = []
    for iteration in range(c["iterations"]):
        flipped = [-v if marks[k] else v for k,v in enumerate(numerators)]
        mean = sum(flipped,Fraction(0))/N
        numerators = [2*mean-v for v in flipped]  # graph-free ideal diffuser
        if sum((a*a for a in numerators),Fraction(0)) != N:
            raise OracleError("exact coherent state is not normalized")
        p = sum((numerators[k]**2 for k in range(N) if marks[k]),
                Fraction(0))/N
        step_summaries.append({"iteration":iteration+1,
                               "success_probability":_fraction(p),
                               "coherent_phase_queries_so_far":6*(iteration+1)})

    marked_amplitude,unmarked_amplitude,closed_success = (
        _independent_two_amplitude(n,len(marked),c["iterations"]))
    if any(a != (marked_amplitude if marks[k] else unmarked_amplitude)
           for k,a in enumerate(numerators)):
        raise OracleError("dense and independent two-dimensional amplitudes disagree")
    success = sum((numerators[k]**2 for k in range(N) if marks[k]),
                  Fraction(0))/N
    if closed_success != success:
        raise OracleError("independent exact probability disagrees")
    ledger = _ledger(c["iterations"],c["verify_measured_candidate"])
    charged = len(ledger)
    expected = 6*c["iterations"] + (3 if c["verify_measured_candidate"] else 0)
    if charged != expected:
        raise OracleError("query accounting discrepancy")
    result = {
        "schema": SCHEMA,
        "config": c,
        "triangle_count": len(marked)//6,
        "marked_ordered_triples":len(marked),
        "uniform_register_basis_size":N,
        "grover_iterations":c["iterations"],
        "query_ledger":ledger,
        "query_count":charged,
        "coherent_oracle_queries":6*c["iterations"],
        "candidate_verification_queries":3 if c["verify_measured_candidate"] else 0,
        "ideal_diffuser_calls":c["iterations"],
        "abstract_uniform_preparations":1,
        "abstract_measurements":1,
        "search_success_probability":_fraction(success),
        "search_failure_probability":_fraction(1-success),
        "marked_amplitude_numerator":_fraction(marked_amplitude),
        "unmarked_amplitude_numerator":_fraction(unmarked_amplitude),
        "probability_denominator":N,
        "iterations":step_summaries,
        "scope":dict(SCOPE),
    }
    result["receipt_sha256"] = digest(result)
    return result


def verify_search(receipt):
    if not isinstance(receipt,dict) or set(receipt)!={
        "schema","config","triangle_count","marked_ordered_triples",
        "uniform_register_basis_size","grover_iterations","query_ledger",
        "query_count","coherent_oracle_queries","candidate_verification_queries",
        "ideal_diffuser_calls","abstract_uniform_preparations",
        "abstract_measurements","search_success_probability",
        "search_failure_probability","marked_amplitude_numerator",
        "unmarked_amplitude_numerator","probability_denominator","iterations",
        "scope","receipt_sha256"
    } or receipt["schema"] != SCHEMA:
        raise OracleError("invalid search receipt schema")
    if receipt["receipt_sha256"] != digest({k:v for k,v in receipt.items()
                                            if k!="receipt_sha256"}):
        raise OracleError("search receipt integrity mismatch")
    calculated = certify_search(receipt["config"])
    if receipt != calculated:
        raise OracleError("search receipt does not pass independent replay")
    return {"verified":True, "query_count":calculated["query_count"],
            "search_success_probability":calculated["search_success_probability"],
            "quantum_speedup_proven":False}


def exhaustive_search_family(n,iterations=1):
    """Finite exhaustive oracle-bounded benchmark on all labeled n=3,4 graphs."""
    if type(n) is not int or n not in (3,4) or type(iterations) is not int or not 0<=iterations<=3:
        raise OracleError("exhaustive family limited to n=3,4, r<=3")
    edges = list(combinations(range(n),2))
    cases = 0
    for mask in range(1<<len(edges)):
        graph={"vertices":n,"edges":[list(e) for j,e in enumerate(edges) if mask>>j&1]}
        receipt=certify_search({"graph":graph,"iterations":iterations,
                                "verify_measured_candidate":False})
        verify_search(receipt)
        cases+=1
    return {"verified":True,"vertices":n,"graphs":cases,
            "iterations":iterations,
            "coherent_oracle_queries_per_program":6*iterations,
            "claims_general_O_n_bound":False}
