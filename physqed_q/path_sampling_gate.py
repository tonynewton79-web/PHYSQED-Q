"""Attack 006: exact H-CCZ perfect-gap promise and path Monte Carlo lower-bound gate.

No claim of BPP != BQP: all explicit instances are classically easy. This
certifies a lower bound against explicitly specified estimation models only.
"""
from dataclasses import dataclass
from fractions import Fraction
from .cubic_bandwidth import CubicPhase
from .dense_bent import make_pair, classify_explicit_pair
from .hccz_circuit import Gate


@dataclass(frozen=True)
class SignProblemCertificate:
    r: int
    n: int
    tilt: int
    quantum_zero_probability: Fraction
    forrelation_numerator: int
    path_sign_mean: Fraction
    path_sign_plus_probability: Fraction
    minimum_single_path_second_moment: int
    minimum_single_path_variance: int
    classical_decision: str


def certify_dense_pair(r: int, *, tilt: int = 0) -> SignProblemCertificate:
    """All-size analytic certificate backed by the established bent-dual identity.

    The proof is given in the matching documentation; this routine does not
    claim to independently prove the Fourier dual for every r by enumeration.
    """
    if type(r) is not int or r < 2:
        raise ValueError('r must be an integer >= 2')
    n = 4*r
    if type(tilt) is not int or not 0 <= tilt < (1 << n):
        raise ValueError('tilt must be an n-bit mask')
    p, g = make_pair(r, tilt=tilt)
    label = classify_explicit_pair(r,p,g)
    if label.decision not in ('YES','NO'):
        raise AssertionError('the explicit generator escaped the declared promise')
    yes = tilt == 0
    S = (1 << (3*n//2)) if yes else 0
    mean = Fraction(S, 1 << (2*n))
    assert mean == (Fraction(1, 1 << (n//2)) if yes else 0)
    return SignProblemCertificate(
        r, n, tilt, Fraction(int(yes)), S, mean,
        (Fraction(1)+mean)/2, 1 << n, (1 << n)-int(yes),
        label.decision,
    )


def phase_to_hccz_gates(phase: CubicPhase, ancilla_one: int, ancilla_two: int):
    """Compile degree <=3 phase ANF to CCZs with TWO basis-|1> ancillas.

    The constant term is a global sign and is returned separately. Both
    ancillas remain exactly |1>. Only the data register receives H gates.
    """
    if not isinstance(phase,CubicPhase):
        raise TypeError('phase must be a CubicPhase')
    if (type(ancilla_one) is not int or type(ancilla_two) is not int
            or ancilla_one==ancilla_two or min(ancilla_one,ancilla_two)<phase.n):
        raise ValueError('two different data-external ancilla indices required')
    gates = []
    global_flip = False
    for mon in phase.monomials:
        indices=[i for i in range(phase.n) if (mon >> i)&1]
        if not indices:
            global_flip=not global_flip
        elif len(indices)==1:
            gates.append(Gate('CCZ',(indices[0],ancilla_one,ancilla_two)))
        elif len(indices)==2:
            gates.append(Gate('CCZ',(indices[0],indices[1],ancilla_one)))
        elif len(indices)==3:
            gates.append(Gate('CCZ',tuple(indices)))
        else:
            raise AssertionError('invalid cubic phase')
    return tuple(gates),(-1 if global_flip else 1)


def hccz_forrelation_program(r: int, *, tilt: int = 0, sign_flip: bool = False):
    """Return (n_wires, basis_input, gates, expected_global_sign).

    Three H^n layers and two diagonal Boolean-phase layers. The two extra
    wires start in |1> and remain so. n=4*r data qubits. Restricted reference
    simulator in Attack005 supports at most 12 total wires, hence r=2 only.
    """
    if type(r) is not int or r < 2:
        raise ValueError('r must be an integer >= 2')
    n=4*r
    p,g=make_pair(r,tilt=tilt,sign_flip=sign_flip)
    anc_one,anc_two=n,n+1
    ps,sp=phase_to_hccz_gates(p,anc_one,anc_two)
    gs,sg=phase_to_hccz_gates(g,anc_one,anc_two)
    hs=tuple(Gate('H',(i,)) for i in range(n))
    program=hs+ps+hs+gs+hs
    initial=(1<<anc_one)|(1<<anc_two)
    return n+2,initial,program,sp*sg


def path_importance_second_moment(n: int, probabilities):
    """Exact E[Y^2] for Y=alpha_z/q(z), alpha_z= +/- 2^(-3n/2).

    This is a one-path full-support importance sampler. The sign is irrelevant
    to its second moment. Exponential explicit probability vectors are allowed
    here *only* for tiny test instances.
    """
    if type(n) is not int or not 1 <= n <= 5:
        raise ValueError('explicit probability reference limited to 1 <= n <= 5')
    probs=tuple(probabilities)
    if len(probs) != 1 << (2*n):
        raise ValueError('one positive probability required for every path')
    if any(not isinstance(p,Fraction) or p<=0 for p in probs):
        raise ValueError('probabilities must be positive exact fractions')
    if sum(probs,Fraction(0))!=1:
        raise ValueError('importance distribution must be normalized')
    return sum((1/p for p in probs),Fraction(0)) / (1 << (3*n))


def exact_sign_only_chi_squared(n: int, samples: int) -> Fraction:
    """Chi-squared(P_yes^m || P_no^m)=(1+2^-n)^m-1.

    Applicable only to independent uniform path signs with labels hidden,
    not to algorithms that read the ANF, sample specific path locations,
    or use a control variate.
    """
    if type(n) is not int or n < 2 or n%2:
        raise ValueError('n must be even and >=2')
    if type(samples) is not int or not 0 <= samples <= 100000:
        raise ValueError('sample count must be an integer in [0,100000]')
    return (Fraction((1<<n)+1,1<<n)**samples)-1


def classical_certificate_shortcut(r:int,tilt:int) -> str:
    """O(r^3) white-box algorithm by checking the explicit mask."""
    return certify_dense_pair(r,tilt=tilt).classical_decision


def iid_importance_mean_mse_lower_bound(r:int, *, tilt: int = 0,
                                        samples:int = 1) -> Fraction:
    """Sharp MSE lower bound for sample mean of unbiased full-path weights."""
    if type(samples) is not int or samples < 1:
        raise ValueError('samples must be a positive integer')
    c=certify_dense_pair(r,tilt=tilt)
    return Fraction(c.minimum_single_path_variance,samples)
