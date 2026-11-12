"""Independent rational odd-sine recurrence and low-order polynomial audit."""
import json
from fractions import Fraction
from physqed_q.attack009_gap import (
    grover_probability, required_grover_iterations_by_quadratic_bound,
    required_polynomial_degree_by_markov,
)


def independent_odd_sine(s, k):
    a=Fraction(1,1<<s)
    prev=a
    curr=3*a-4*a*a*a
    if k==0:return a*a
    if k==1:return curr*curr
    c=1-2*a*a
    for _ in range(1,k):
        prev,curr=curr,2*c*curr-prev
    return curr*curr


def truncated_chebyshev_coefficients(k):
    """Return constant, p and p^2 coefficients of Grover probability."""
    t0=(1,0,0)
    t1=(1,-2,0)
    if k==0:return (0,1,0)
    for _ in range(1,2*k+1):
        shifted=(t1[0],t1[1]-2*t1[0],t1[2]-2*t1[1])
        new=tuple(2*shifted[j]-t0[j] for j in range(3))
        t0,t1=t1,new
    return ((1-t1[0])//2,-t1[1]//2,-t1[2]//2)


def run():
    checks=0
    for s in range(1,12):
        for k in range(30):
            p=Fraction(1,1<<(2*s))
            assert grover_probability(p,k)==independent_odd_sine(s,k)
            checks+=1
    derivatives=0
    for k in range(40):
        c=truncated_chebyshev_coefficients(k)
        assert c[0]==0 and c[1]==(2*k+1)**2 and c[2]<=0
        derivatives+=1
    bounds=0
    for n in range(1,41):
        w=n-1
        k=required_grover_iterations_by_quadratic_bound(n,w)
        d=required_polynomial_degree_by_markov(n,w)
        p=Fraction(1,1<<(2*(n+w)))
        assert (2*k+1)**2*p>=Fraction(2,3)
        assert 2*d*d*p>=Fraction(1,3)
        bounds+=1
    return {"odd_sine_recurrence_cases":checks,
            "chebyshev_coefficient_cases":derivatives,
            "unique_sat_integer_bounds":bounds,
            "n5":{"p":"1/262144","necessary_grover_iterations":209,
                  "necessary_markov_degree":210},
            "status":"PASS_RESTRICTED_MODEL_ONLY__BPP_BQP_OPEN"}


if __name__=="__main__":
    print(json.dumps(run(),indent=2))
