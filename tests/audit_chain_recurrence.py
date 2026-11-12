"""Independent standard-library 16-state transfer recurrence certificate.

Checks an all-order row identity, rather than guessing recurrence from data.
"""
import json
from fractions import Fraction
from physqed_q.cubic_bandwidth import consecutive_cubic_chain, exact_banded_forrelation


def signed_transfer_rows():
    T=[[0]*16 for _ in range(16)]
    for src in range(16):
        for xy in range(4):
            bits=(src<<2)|xy
            x_cubic=(bits&0b010101)==0b010101
            y_cubic=(bits&0b101010)==0b101010
            cross=(xy==3)
            sign=-1 if (x_cubic ^ y_cubic ^ cross) else 1
            T[bits&15][src]+=sign
    return T


def step_row(row,T):
    return [sum(row[dst]*T[dst][src] for dst in range(16))
            for src in range(16)]


def audit():
    T=signed_transfer_rows()
    row=[1]*16
    rows={0:row}
    for power in range(1,7):
        row=step_row(row,T)
        rows[power]=row
    assert [rows[6][i]-4*rows[4][i] for i in range(16)]==[16]*16
    assert rows[4]==[16,16,16,16,16,16,16,0,16,16,16,0,16,16,16,0]
    assert rows[6]==[80,80,80,80,80,80,80,16,80,80,80,16,80,80,80,16]
    base={}
    for n in range(2,8):
        if n==2:
            signed=4
        else:
            phase=consecutive_cubic_chain(n)
            signed=exact_banded_forrelation(phase,phase).signed_sum
        base[n]=signed
    assert [base[n] for n in range(2,8)]==[4,4,16,32,80,160]
    sequence=base.copy()
    for n in range(2,390):
        sequence[n+6]=4*sequence[n+4]+16*sequence[n]
    for n in range(3,111):
        phase=consecutive_cubic_chain(n)
        got=exact_banded_forrelation(phase,phase)
        assert got.signed_sum==sequence[n]
    for n in range(2,396):
        assert sequence[n]>0
        assert sequence[n]*4**n<=9**n
    c=Fraction(9,4)
    assert c**6-4*c**4-16==Fraction(46001,4096)>0
    return dict(row_identity="ones*T^6 - 4*ones*T^4 = 16*ones",
                signed_base=[base[n] for n in range(2,8)],
                recurrence="S_(n+6) = 4*S_(n+4) + 16*S_n for n>=2",
                exact_decay="Phi_n^2 <= (81/128)^n for n>=2",
                n_crosschecks=108,n_rational_bound_checks=394,
                status="PASS; no BPP-versus-BQP separation")


if __name__=="__main__":
    print(json.dumps(audit(),indent=2))
