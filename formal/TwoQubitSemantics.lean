import GateIdentities

/-!
  Explicit two-qubit basis-column semantics. Qubit 0 is the least-significant
  computational-basis bit, agreeing with PHYSQED-Q's Python convention.
  An operator is defined by the images of all four basis vectors.
-/

namespace PHYSQEDQ

structure State4 where
  v0 : Exact
  v1 : Exact
  v2 : Exact
  v3 : Exact
  deriving Repr

def subE (x y : Exact) : Exact := addE x (negE y)

inductive QGate where
  | h0 | h1 | x0 | x1 | z0 | z1
  | s0 | s1 | sdg0 | sdg1 | t0 | t1 | tdg0 | tdg1
  | cnot01 | cnot10 | cz | swap
  deriving DecidableEq, Repr

def act (g : QGate) (v : State4) : State4 :=
  match g with
  | .h0 =>
      ⟨mulE invSqrtTwo (addE v.v0 v.v1),
       mulE invSqrtTwo (subE v.v0 v.v1),
       mulE invSqrtTwo (addE v.v2 v.v3),
       mulE invSqrtTwo (subE v.v2 v.v3)⟩
  | .h1 =>
      ⟨mulE invSqrtTwo (addE v.v0 v.v2),
       mulE invSqrtTwo (addE v.v1 v.v3),
       mulE invSqrtTwo (subE v.v0 v.v2),
       mulE invSqrtTwo (subE v.v1 v.v3)⟩
  | .x0 => ⟨v.v1, v.v0, v.v3, v.v2⟩
  | .x1 => ⟨v.v2, v.v3, v.v0, v.v1⟩
  | .z0 => ⟨v.v0, negE v.v1, v.v2, negE v.v3⟩
  | .z1 => ⟨v.v0, v.v1, negE v.v2, negE v.v3⟩
  | .s0 => ⟨v.v0, mulE imag v.v1, v.v2, mulE imag v.v3⟩
  | .s1 => ⟨v.v0, v.v1, mulE imag v.v2, mulE imag v.v3⟩
  | .sdg0 => ⟨v.v0, mulE negImag v.v1, v.v2, mulE negImag v.v3⟩
  | .sdg1 => ⟨v.v0, v.v1, mulE negImag v.v2, mulE negImag v.v3⟩
  | .t0 => ⟨v.v0, mulE tPhase v.v1, v.v2, mulE tPhase v.v3⟩
  | .t1 => ⟨v.v0, v.v1, mulE tPhase v.v2, mulE tPhase v.v3⟩
  | .tdg0 => ⟨v.v0, mulE tdgPhase v.v1, v.v2, mulE tdgPhase v.v3⟩
  | .tdg1 => ⟨v.v0, v.v1, mulE tdgPhase v.v2, mulE tdgPhase v.v3⟩
  | .cnot01 => ⟨v.v0, v.v3, v.v2, v.v1⟩
  | .cnot10 => ⟨v.v0, v.v1, v.v3, v.v2⟩
  | .cz => ⟨v.v0, v.v1, v.v2, negE v.v3⟩
  | .swap => ⟨v.v0, v.v2, v.v1, v.v3⟩

def runCircuit (gates : List QGate) (start : State4) : State4 :=
  gates.foldl (fun v g => act g v) start

def basis0 : State4 := ⟨one, zero, zero, zero⟩
def basis1 : State4 := ⟨zero, one, zero, zero⟩
def basis2 : State4 := ⟨zero, zero, one, zero⟩
def basis3 : State4 := ⟨zero, zero, zero, one⟩

structure Operator4 where
  col0 : State4
  col1 : State4
  col2 : State4
  col3 : State4

def operator (gates : List QGate) : Operator4 :=
  ⟨runCircuit gates basis0, runCircuit gates basis1,
   runCircuit gates basis2, runCircuit gates basis3⟩

def stateEq (x y : State4) : Prop :=
  eEq x.v0 y.v0 ∧ eEq x.v1 y.v1 ∧
  eEq x.v2 y.v2 ∧ eEq x.v3 y.v3

def operatorEq (x y : Operator4) : Prop :=
  stateEq x.col0 y.col0 ∧ stateEq x.col1 y.col1 ∧
  stateEq x.col2 y.col2 ∧ stateEq x.col3 y.col3

-- Orientation and phase sanity checks for the independent Lean model.
theorem h0_basis0 :
    stateEq (act .h0 basis0)
      ⟨invSqrtTwo, invSqrtTwo, zero, zero⟩ := by
  unfold stateEq eEq qEq
  decide

theorem h1_basis0 :
    stateEq (act .h1 basis0)
      ⟨invSqrtTwo, zero, invSqrtTwo, zero⟩ := by
  unfold stateEq eEq qEq
  decide

theorem cnot01_basis1 : stateEq (act .cnot01 basis1) basis3 := by
  unfold stateEq eEq qEq
  decide

theorem cnot10_basis2 : stateEq (act .cnot10 basis2) basis3 := by
  unfold stateEq eEq qEq
  decide

theorem swap_basis1 : stateEq (act .swap basis1) basis2 := by
  unfold stateEq eEq qEq
  decide

theorem cz_basis3 :
    stateEq (act .cz basis3) ⟨zero, zero, zero, negOne⟩ := by
  unfold stateEq eEq qEq
  decide

end PHYSQEDQ
