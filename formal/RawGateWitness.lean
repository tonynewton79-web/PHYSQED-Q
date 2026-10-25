import RawGateBridge

set_option maxRecDepth 10000
set_option maxHeartbeats 0

open PHYSQEDQ

def witnessRawInput : List RawGate :=
  [("H", [0]), ("Z", [0]), ("H", [0]),
   ("CNOT", [0, 1]), ("CNOT", [0, 1]),
   ("T", [0]), ("T", [0])]

def witnessRawOutput : List RawGate := [("X", [0]), ("S", [0])]

theorem witnessRawFullOperatorEquality :
    rawOperatorEq witnessRawInput witnessRawOutput := by
  unfold rawOperatorEq
  decide
