"""Exact oracle, coherent superposition, family, receipt and adversarial tests."""
import copy
from itertools import combinations
import unittest

from physqed_q.kernel import ONE, NEG_ONE, ZERO, INV_ROOT_TWO
from physqed_q.adjacency_oracle import (
    OracleError, PROGRAM_SCHEMA, basis, certify, digest, evolve,
    evolve_sparse, family_triangle_phase, graph_normalize, layout,
    program_normalize, query_map, replay, triangle_phase_program,
)


def query_program(n):
    return {"schema":PROGRAM_SCHEMA,"name":"single-query","vertices":n,
            "vertex_registers":["u","v"],"answer_registers":["b"],
            "operations":[{"op":"QUERY","left":"u","right":"v","answer":"b"}]}


class ExactGraphOracleTests(unittest.TestCase):
    def test_truth_table_including_invalid_labels_and_involution(self):
        for n in (3,4):
            pairs=list(combinations(range(n),2))
            p=program_normalize(query_program(n))
            k,vs,ans,_=layout(p)
            for mask in range(1<<len(pairs)):
                e=[list(pair) for j,pair in enumerate(pairs) if mask>>j&1]
                g={"vertices":n,"edge_set":frozenset(map(tuple,e))}
                for u in range(1<<k):
                    for v in range(1<<k):
                        for bit in (0,1):
                            i=basis(p,{"u":u,"v":v},{"b":bit})
                            j=query_map(p,g,p["operations"][0],i)
                            flipped=int(0<=u<n and 0<=v<n and
                                        tuple(sorted((u,v))) in g["edge_set"])
                            self.assertEqual(j,basis(p,{"u":u,"v":v},{"b":bit^flipped}))
                            self.assertEqual(query_map(p,g,p["operations"][0],j),i)

    def test_entangled_state_from_coherent_query(self):
        p=query_program(2)
        p["operations"]=[{"op":"X","bit":1},{"op":"H","bit":0},*p["operations"]]
        g={"vertices":2,"edges":[[0,1]]}
        state,ledger=evolve(p,g)
        self.assertEqual(len(ledger),1)
        self.assertEqual(sum(x!=ZERO for x in state),2)
        self.assertEqual(state[basis(p,{"u":0,"v":1},{"b":1})],INV_ROOT_TWO)
        self.assertEqual(state[basis(p,{"u":1,"v":1},{"b":0})],INV_ROOT_TWO)
        sparse,events=evolve_sparse(p,g)
        self.assertEqual(sparse,{i:a for i,a in enumerate(state) if a!=ZERO})
        self.assertEqual(events,ledger)

    def test_one_query_phase_kickback(self):
        p=query_program(2)
        answer=layout(p)[2]["b"]
        p["operations"]=[{"op":"X","bit":answer},{"op":"H","bit":answer},*p["operations"]]
        i=basis(p,{"u":0,"v":1})
        state,ledger=evolve(p,{"vertices":2,"edges":[[0,1]]},i)
        self.assertEqual(len(ledger),1)
        self.assertEqual(state[i],-INV_ROOT_TWO)
        self.assertEqual(state[i^(1<<answer)],INV_ROOT_TWO)

    def test_fixed_triple_phase_all_graphs(self):
        self.assertEqual(family_triangle_phase(3)["cases"],8)
        self.assertEqual(family_triangle_phase(4)["cases"],256)

    def test_six_query_receipt_replays(self):
        p=triangle_phase_program(3)
        i=basis(p,{"u":0,"v":1,"w":2})
        g={"vertices":3,"edges":[[0,1],[0,2],[1,2]]}
        receipt=certify(p,g,i)
        self.assertEqual(receipt["query_count"],6)
        self.assertEqual(receipt["final_state"],[{"basis":i,"coefficients":["-1","0","0","0"]}])
        self.assertTrue(replay(receipt)["verified"])
        self.assertFalse(receipt["scope"]["quantum_query_complexity_theorem_proven"])

    def test_negative_graph_not_marked(self):
        p=triangle_phase_program(3)
        i=basis(p,{"u":0,"v":1,"w":2})
        r=certify(p,{"vertices":3,"edges":[[0,1],[1,2]]},i)
        self.assertEqual(r["query_count"],6)
        self.assertEqual(r["final_state"],[{"basis":i,"coefficients":["1","0","0","0"]}])

    def test_forged_query_count_and_events_rejected_with_new_hash(self):
        r=certify(query_program(3),{"vertices":3,"edges":[[0,1]]})
        for key, value in (("query_count",0),("query_ledger",[]),("gate_count",0),
                           ("final_state",[]),("scope",{**r["scope"],
                               "quantum_query_complexity_theorem_proven":True})):
            changed=copy.deepcopy(r)
            changed[key]=value
            changed["receipt_sha256"]=digest({k:v for k,v in changed.items()
                                                 if k!="receipt_sha256"})
            with self.subTest(key=key), self.assertRaises(OracleError):
                replay(changed)

    def test_corrupted_digest_rejected(self):
        r=certify(query_program(3),{"vertices":3,"edges":[]})
        r["receipt_sha256"]="0"*64
        with self.assertRaises(OracleError):
            replay(r)

    def test_unmetered_graph_access_refused(self):
        p=query_program(3)
        p["operations"]=[{"op":"GRAPH_LOOKUP","left":"u","right":"v","answer":"b"}]
        with self.assertRaises(OracleError):
            program_normalize(p)

    def test_invalid_graph_or_out_of_scope_refused(self):
        for graph in ({"vertices":3,"edges":[[0,0]]},
                      {"vertices":3,"edges":[[0,1],[0,1]]},
                      {"vertices":3,"edges":[[1,0]]},
                      {"vertices":3,"edges":[[0,3]]}):
            with self.subTest(graph=graph),self.assertRaises(OracleError):
                graph_normalize(graph)
        p=query_program(8)
        p["vertex_registers"]=["u","v","w"]
        p["answer_registers"]=["a","b","c"]
        self.assertEqual(layout(program_normalize(p))[3],12)
        p["answer_registers"].append("d")
        with self.assertRaises(OracleError):
            program_normalize(p)

    def test_padded_and_zero_oracle_still_costs_one(self):
        p=query_program(3)
        for u,v in ((0,0),(3,0),(3,3),(1,2)):
            start=basis(p,{"u":u,"v":v})
            out,ledger=evolve(p,{"vertices":3,"edges":[[0,1]]},start)
            self.assertEqual(out[start],ONE)
            self.assertEqual(len(ledger),1)


if __name__=="__main__":
    unittest.main()
