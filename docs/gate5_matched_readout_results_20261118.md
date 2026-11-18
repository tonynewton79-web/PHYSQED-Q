# PHYSQED-Q Gate 5 — measurement-controlled classical readout and mitigation

**Status:** restricted, post-hoc numerical model result; NOT live hardware,
not a general T-count or superconducting-fidelity superiority finding.

## Provenance

- Research PR: https://github.com/tonynewton79-web/PHYSQED-Q/pull/26
- First fully successful hosted Gate 5 run:
  https://github.com/tonynewton79-web/PHYSQED-Q/actions/runs/44290094946
- Independently replayed first complete source commit:
  6bff6a553d779de187d1b949704cc2be3e42e6a7
- First successful hosted complete-results ZIP sha256:
  04cc52148d82eda79449d29a392544198dc0ea87a48f1e38da3dd03f13ca52f0
- Upstream historical Gate 4 ZIP sha256:
  ca73cddcfb8aa594ef80212e5d1e4037469d91e89b2d882341d803b5e043d510
- Locked application manifest:
  edb6322110fe59e6fd1250c124cd0a3b8a9782d3a1975a1d0b5e51f01da247f6

## A reproducible negative control for spurious physical superiority

Using the same pre-readout historical simulated output for each candidate,
counterfactually assign exactly the same *classical readout-error channel*
to PHYSQED-Q and PyZX. This does NOT change the actual native quantum
circuit or physical layout and therefore is NOT a newly executable
matched-layout hardware experiment.

For the three-qubit phase-cancellation circuit, signed TVD
(PHYSQED-Q minus PyZX, negative favours PHYSQED-Q):

| Comparison | FakeManilaV2 | FakeLagosV2 |
| --- | ---: | ---: |
| Archived original measurement assignment | -0.06184818 | -0.31437704 |
| Both with PHYSQED-Q readout assignment | +0.01244716 | +0.01040894 |
| Both with PyZX readout assignment | +0.01050758 | +0.00103574 |
| Pre-readout gate noise only | +0.01237941 | +0.01414907 |
| Exact-known-model classical readout inversion | +0.01237941 | +0.01414907 |

The original reported advantage is reversed by matching the classical
measurement assignment; it is not evidence of lower PHYSQED gate noise.
For all five selected application cases per backend, comparison
PHYSQED-Q versus PyZX changes from 3 lower TVD, 1 tie, 1 higher under
the original readout assignments to 2 lower, 1 tie, 2 higher under
either common readout assignment. PHYSQED-Q ties Qiskit in each case.
All comparisons are restricted to the purpose-selected five cases.

## Finite-shot mitigation is ill-conditioned

The historical 3-bit readout assignment matrix has condition number
approximately 1.39 on FakeManilaV2 and 28.68 on FakeLagosV2.
Exact-parameter inversion can recover the true gate-noise probabilities
from noiseless model output but can greatly amplify empirical shot noise.

50 independent synthetic multinomial draws per method/shot count,
separate seeds, followed by inverse and Euclidean probability-simplex
projection (which introduces bias), give:

| Historical backend | Simulated shots | Median PHYSQED mitigated TVD | Median PyZX mitigated TVD |
| --- | ---: | ---: | ---: |
| FakeManilaV2 | 8,192 | 0.01810 | 0.00978 |
| FakeManilaV2 | 65,536 | 0.01561 | 0.00407 |
| FakeLagosV2 | 8,192 | 0.15894 | 0.10850 |
| FakeLagosV2 | 65,536 | 0.05558 | 0.04710 |

These are sample medians only, not statistically significant
experimental gains or confidence intervals on physical device error.
Real calibration uncertainty and drift are omitted.

For a binary-symmetric readout with flip rate e,
the observed frequency q=e+(1-2e)p.
Under exact e, the naive inverse estimator has
Var[p_hat] = q(1-q)/[N(1-2e)^2].
The historical Lagos physical-qubit-2 flip rate e=0.4638 yields an
inverse sensitivity 1/(1-2e) about 13.81 on that qubit.
This identity and linear algebra are established prior art.

## Exact verification

The original hosted run performed real pinned Qiskit/Aer/PyZX simulation
upstream via the Gate 4 source; Gate 5 applies counterfactual classical
channels and synthetic finite-shot sampling. The independent second-pass
auditor implements readout matrices by explicit bit-index loops rather
than the primary optimizer's Kronecker construction. It passed 280
numeric metric checks and independently recomputed all 400 retained
finite-shot trial statistics. The full original report is available
in the hosted GitHub Actions artifact.

This is an exact numerical-model verification, NOT an independent
quantum dynamics solver or empirical device replication.

## Next physical gate

Requires independent application circuits and live processor access.
Predeclare a hardware endpoint and use:
- identical physical measured-output allocation or explicit shared
  allocation optimization;
- dated native gate and readout calibrations, with calibration uncertainty;
- interleaved randomized physical shots under matched routing conditions;
- baseline Qiskit and PyZX native implementations;
- readout mitigation whose variance/bias are reported, not hidden.

No PHYSQED-Q general T-count, physical gate-noise, or device-fidelity
superiority has been established by these tests.
