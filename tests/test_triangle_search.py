"""Scope-correct exact coherent triangle search and measurement regression."""
from __future__ import annotations
from copy import deepcopy
from fractions import Fraction
from itertools import combinations
import unittest

from physqed_q.adjacency_oracle import OracleError, digest
from physqed_q.triangle_search import (
    SCHEMA, SCOPE, canonical_config, certify_search, verify_search,
    exhaustive_search_family,
)


def config(n, edges, iterations=1, verify=False):
    return {"graph":{"vertices":n,"edges":sorted([list(e) for e in edges])},
            "iterations":iterations,"verify_measured_candidate":verify}


class ExactCoherentTriangleSearch(unittest.TestCase):
    def test_complete_n3_exact_measurement_and_query_ledger(self):
        c=config(3,combinations(range(3),2),1,True)
        receipt=certify_search(c)
        self.assertEqual(receipt["triangle_count"],1)
        self.assertEqual(receipt["marked_ordered_triples"],6)
        self.assertEqual(receipt["uniform_register_basis_size"],27)
        self.assertEqual(receipt["search_success_probability"],"722/729")
        self.assertEqual(receipt["search_failure_probability"],"7/729")
        self.assertEqual(receipt["coherent_oracle_queries"],6)
        self.assertEqual(receipt["candidate_verification_queries"],3)
        self.assertEqual(receipt["query_count"],9)
        distribution=receipt["final_measurement_distribution"]
        self.assertEqual(len(distribution),27)
        self.assertEqual(sum((Fraction(x["probability"]) for x in distribution),
                             Fraction(0)),1)
        marked_outcomes=[x for x in distribution if set(x["triple"])=={0,1,2}]
        self.assertEqual(len(marked_outcomes),6)
        self.assertEqual(sum((Fraction(x["probability"]) for x in marked_outcomes),
                             Fraction(0)),Fraction(722,729))
        self.assertEqual(len(receipt["query_ledger"]),9)
        self.assertTrue(verify_search(receipt)["verified"])
        self.assertFalse(receipt["scope"]["O_n_query_algorithm_proven"])

    def test_empty_graph_keeps_uniform_distribution(self):
        for iterations in range(4):
            receipt=certify_search(config(4,[],iterations))
            self.assertEqual(receipt["search_success_probability"],"0/1")
            self.assertEqual(receipt["search_failure_probability"],"1/1")
            self.assertEqual(receipt["query_count"],6*iterations)
            self.assertEqual(receipt["unmarked_amplitude_numerator"],"1/1")

    def test_known_n4_single_triangle(self):
        r=certify_search(config(4,((0,1),(0,2),(1,2))))
        self.assertEqual(r["triangle_count"],1)
        self.assertEqual(r["search_success_probability"],"1323/2048")
        self.assertEqual(r["query_count"],6)

    def test_complete_n4_one_iteration(self):
        r=certify_search(config(4,combinations(range(4),2)))
        self.assertEqual(r["triangle_count"],4)
        self.assertEqual(r["search_success_probability"],"27/32")
        self.assertEqual(r["query_count"],6)
        self.assertEqual(Fraction(r["search_success_probability"]) +
                         Fraction(r["search_failure_probability"]),1)

    def test_multiple_exact_search_iterations(self):
        r=certify_search(config(4,((0,1),(0,2),(1,2)),3,True))
        self.assertEqual(r["query_count"],21)
        self.assertEqual(r["coherent_oracle_queries"],18)
        self.assertEqual(r["candidate_verification_queries"],3)
        self.assertEqual(len(r["iterations"]),3)
        self.assertTrue(verify_search(r)["verified"])

    def test_exhaustive_all_graphs_n3_and_n4(self):
        a=exhaustive_search_family(3,iterations=2)
        b=exhaustive_search_family(4,iterations=1)
        self.assertEqual(a["graphs"],8)
        self.assertEqual(b["graphs"],64)
        self.assertTrue(a["verified"] and b["verified"])

    def test_no_false_free_queries_or_algorithmic_proof(self):
        r=certify_search(config(3,[(0,1),(0,2),(1,2)]))
        self.assertFalse(r["scope"]["quantum_speedup_proven"])
        self.assertFalse(r["scope"]["gate_implementation_proven"])
        self.assertFalse(r["scope"]["O_n_query_algorithm_proven"])
        self.assertEqual(r["oracle_phase_calls"] if "oracle_phase_calls" in r else r["grover_iterations"],1)
        self.assertEqual(r["query_count"],6)

    def test_replay_rejects_tampered_probability(self):
        r=certify_search(config(3,[(0,1),(0,2),(1,2)]))
        broken=deepcopy(r)
        broken["search_success_probability"]="1/1"
        with self.assertRaises(OracleError):
            verify_search(broken)
        # An attacker recomputing the hash cannot fabricate the probability.
        broken["receipt_sha256"]=digest({k:v for k,v in broken.items()
                                         if k!="receipt_sha256"})
        with self.assertRaises(OracleError):
            verify_search(broken)

    def test_replay_rejects_forged_measurement_distribution(self):
        r=certify_search(config(3,[(0,1),(0,2),(1,2)]))
        wrong=deepcopy(r)
        wrong["final_measurement_distribution"][0]["probability"]="0/1"
        wrong["receipt_sha256"]=digest({k:v for k,v in wrong.items()
                                         if k!="receipt_sha256"})
        with self.assertRaises(OracleError):
            verify_search(wrong)

    def test_replay_rejects_forged_count(self):
        r=certify_search(config(3,[(0,1),(0,2),(1,2)],2))
        broken=deepcopy(r)
        broken["query_count"]-=1
        broken["receipt_sha256"]=digest({k:v for k,v in broken.items()
                                         if k!="receipt_sha256"})
        with self.assertRaises(OracleError):
            verify_search(broken)

    def test_replay_rejects_ledger_edit(self):
        r=certify_search(config(3,[(0,1),(0,2),(1,2)]))
        broken=deepcopy(r)
        broken["query_ledger"][0]["right"]="w"
        broken["receipt_sha256"]=digest({k:v for k,v in broken.items()
                                         if k!="receipt_sha256"})
        with self.assertRaises(OracleError):
            verify_search(broken)

    def test_scope_refuses_unbounded_or_incomplete_programs(self):
        with self.assertRaises(OracleError):
            certify_search(config(4,[],13))
        with self.assertRaises(OracleError):
            certify_search(config(9,[],1))
        with self.assertRaises(OracleError):
            certify_search({"graph":{"vertices":3,"edges":[]},"iterations":1})
        with self.assertRaises(OracleError):
            certify_search(config(3,[],True))
        with self.assertRaises(OracleError):
            bad=config(3,[(1,2),(0,1)],1)
            bad["graph"]["edges"]=[[1,2],[0,1]]
            certify_search(bad)

    def test_program_receipt_schema_is_frozen(self):
        r=certify_search(config(3,[],0))
        self.assertEqual(r["schema"],SCHEMA)
        self.assertEqual(r["scope"],SCOPE)
        self.assertEqual(r["query_count"],0)
        self.assertEqual(r["search_success_probability"],"0/1")
        self.assertTrue(verify_search(r)["verified"])


if __name__=="__main__":
    unittest.main()
