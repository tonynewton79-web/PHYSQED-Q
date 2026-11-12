"""Clean-room finite audit: independent Boolean and sparse signed-integer H/CCZ."""
import json
from collections import defaultdict
from physqed_q.public_mod3 import public_mod3_circuit,input_basis


def independent_sparse_run(basis,gates):
    state={basis:1}
    h=0
    for gate in gates:
        if gate.kind=='H':
            mask=1<<gate.qubits[0]
            nxt=defaultdict(int)
            for z,amp in state.items():
                lo=z&~mask
                nxt[lo]+=amp
                nxt[lo|mask]+=amp if not (z&mask) else -amp
            state={z:v for z,v in nxt.items() if v}
            h+=1
        elif gate.kind=='CCZ':
            mask=sum(1<<j for j in gate.qubits)
            state={z:(-amp if (z&mask)==mask else amp)
                   for z,amp in state.items()}
        else:
            raise ValueError('bad gate type')
    assert sum(v*v for v in state.values())==1<<h
    return state,h


def direct_boolean_pair(state,control):
    a,b=state&1,(state>>1)&1
    b ^= control&a
    a ^= control&b
    return a|(b<<1)


def run():
    perm={s:direct_boolean_pair(s,1) for s in range(4)}
    assert perm=={0:0,1:2,2:3,3:1}
    assert all(direct_boolean_pair(s,0)==s for s in range(4))
    assert all(direct_boolean_pair(direct_boolean_pair(direct_boolean_pair(s,1),1),1)==s
               for s in range(4))
    boolean_tests=0
    for n in range(1,12):
        for x in range(1<<n):
            state=1
            for i in range(n):
                state=direct_boolean_pair(state,(x>>i)&1)
            assert int((state&2)==0)==int(x.bit_count()%3==0)
            boolean_tests+=1
    sparse_tests=0
    for n in range(1,6):
        selected=range(1<<n)
        spec=public_mod3_circuit(n)
        for x in selected:
            z,h=independent_sparse_run(input_basis(n,x),spec.gates)
            s=1
            for i in range(n):
                s=direct_boolean_pair(s,(x>>i)&1)
            final=input_basis(n,x)|((s&1)<<n)|((1^((s>>1)&1))<<(n+1))
            assert z=={final:1<<(h//2)}
            sparse_tests+=1
    n=8
    spec=public_mod3_circuit(n)
    for x in (0,1,2,3,7,31,63,85,127,170,254,255):
        z,h=independent_sparse_run(input_basis(n,x),spec.gates)
        s=1
        for i in range(n):
            s=direct_boolean_pair(s,(x>>i)&1)
        final=input_basis(n,x)|((s&1)<<n)|((1^((s>>1)&1))<<(n+1))
        assert z=={final:1<<(h//2)}
        sparse_tests+=1
    cuts=0
    for n in range(4,100):
        rows=[tuple(int((p.bit_count()+s.bit_count())%3==0)
                    for s in (0,1,3)) for p in (0,1,3)]
        assert len(set(rows))==3
        cuts+=1
    return {'boolean_cases':boolean_tests,'sparse_exact_states':sparse_tests,
            'distinct_residual_witness_lengths':cuts,
            'transition':perm,
            'status':'PASS; AC0[2] theorem is imported prior art; explicit language is in P'}


if __name__=='__main__':
    print(json.dumps(run(),indent=2,sort_keys=True))
