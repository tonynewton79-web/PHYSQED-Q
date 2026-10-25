import TwoQubitSemantics

set_option maxRecDepth 10000
set_option maxHeartbeats 0

open PHYSQEDQ

def inputGates : List QGate :=
  [.h0, .z0, .h0, .cnot01, .cnot01, .t0, .t0]
def outputGates : List QGate := [.x0, .s0]

-- A specific complete two-qubit operator identity, not an arbitrary theorem.
theorem exactOperatorCertificate :
    operatorEq (operator inputGates) (operator outputGates) := by
  unfold operatorEq stateEq eEq qEq
  decide
