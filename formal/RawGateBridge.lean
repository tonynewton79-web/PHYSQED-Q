import TwoQubitSemantics

/-!
  Decode receipt gate strings and explicit qubit positions *inside Lean*.
  An unrecognised name, wrong arity, out-of-range index, or reversed ordered
  control where unsupported yields `none`, never a silently skipped gate.
  This decoder covers the two-qubit alphabet only.
-/

namespace PHYSQEDQ

abbrev RawGate := String × List Nat

def decodeGate : RawGate → Option QGate
  | ("H", [0]) => some .h0
  | ("H", [1]) => some .h1
  | ("X", [0]) => some .x0
  | ("X", [1]) => some .x1
  | ("Z", [0]) => some .z0
  | ("Z", [1]) => some .z1
  | ("S", [0]) => some .s0
  | ("S", [1]) => some .s1
  | ("SDG", [0]) => some .sdg0
  | ("SDG", [1]) => some .sdg1
  | ("T", [0]) => some .t0
  | ("T", [1]) => some .t1
  | ("TDG", [0]) => some .tdg0
  | ("TDG", [1]) => some .tdg1
  | ("CNOT", [0, 1]) => some .cnot01
  | ("CNOT", [1, 0]) => some .cnot10
  | ("CZ", [0, 1]) => some .cz
  | ("CZ", [1, 0]) => some .cz
  | ("SWAP", [0, 1]) => some .swap
  | ("SWAP", [1, 0]) => some .swap
  | _ => none

def decodeCircuit (rows : List RawGate) : Option (List QGate) :=
  rows.mapM decodeGate

-- Executable Boolean presentations of the same exact cross-multiplied
-- coefficient equalities used by TwoQubitSemantics.operatorEq.
def fractionMatches (x y : Fraction) : Bool :=
  decide (x.num * Int.ofNat y.den = y.num * Int.ofNat x.den)

def exactMatches (x y : Exact) : Bool :=
  fractionMatches x.a y.a && fractionMatches x.b y.b &&
  fractionMatches x.c y.c && fractionMatches x.d y.d

def stateMatches (x y : State4) : Bool :=
  exactMatches x.v0 y.v0 && exactMatches x.v1 y.v1 &&
  exactMatches x.v2 y.v2 && exactMatches x.v3 y.v3

def operatorMatches (x y : Operator4) : Bool :=
  stateMatches x.col0 y.col0 && stateMatches x.col1 y.col1 &&
  stateMatches x.col2 y.col2 && stateMatches x.col3 y.col3

theorem operatorMatches_correct (x y : Operator4) :
    operatorMatches x y = true ↔ operatorEq x y := by
  simp [operatorMatches, stateMatches, exactMatches, fractionMatches,
    operatorEq, stateEq, eEq, qEq, and_assoc]

-- The witness predicate is deliberately Boolean to ensure the proof kernel
-- evaluates complete decoded words before checking the result.
def rawOperatorMatches (lhs rhs : List RawGate) : Bool :=
  match decodeCircuit lhs, decodeCircuit rhs with
  | some l, some r => operatorMatches (operator l) (operator r)
  | _, _ => false

-- Malformed input evaluates to false; no partial interpretation.
def rawOperatorEq (lhs rhs : List RawGate) : Prop :=
  rawOperatorMatches lhs rhs = true

theorem h0_raw_decode : decodeGate ("H", [0]) = some .h0 := by decide
theorem cnot_reversed_raw_decode :
    decodeGate ("CNOT", [1, 0]) = some .cnot10 := by decide
theorem cz_reversed_raw_decode :
    decodeGate ("CZ", [1, 0]) = some .cz := by decide
theorem invalid_raw_decode : decodeGate ("H", [2]) = none := by decide
theorem invalid_arity_decode : decodeGate ("H", [0, 1]) = none := by decide
theorem unknown_gate_decode : decodeGate ("UNKNOWN", [0]) = none := by decide

end PHYSQEDQ
