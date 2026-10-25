import Init

/-!
  PHYSQED-Q: a restricted, independently kernel-checked catalogue of gate identities.

  Each `Exact` denotes (a + b * √2) + i * (c + d * √2) for rational a,b,c,d.
  Rational coefficients use explicit numerator/denominator pairs. Extensional
  equality is exact integer cross multiplication; no floating point is involved.
  No floating-point approximation or unchecked proof steps are used.
  This is not a proof about the Python interpreter or about receipt verification.
-/

namespace PHYSQEDQ

structure Fraction where
  num : Int
  den : Nat
  deriving Repr

def q0 : Fraction := ⟨0, 1⟩
def q1 : Fraction := ⟨1, 1⟩
def qm1 : Fraction := ⟨-1, 1⟩
def q2 : Fraction := ⟨2, 1⟩
def qHalf : Fraction := ⟨1, 2⟩
def qmHalf : Fraction := ⟨-1, 2⟩

def qAdd (x y : Fraction) : Fraction :=
  ⟨x.num * Int.ofNat y.den + y.num * Int.ofNat x.den,
   x.den * y.den⟩

def qNeg (x : Fraction) : Fraction := ⟨-x.num, x.den⟩
def qSub (x y : Fraction) : Fraction := qAdd x (qNeg y)
def qMul (x y : Fraction) : Fraction := ⟨x.num * y.num, x.den * y.den⟩
def qEq (x y : Fraction) : Prop :=
  x.num * Int.ofNat y.den = y.num * Int.ofNat x.den

structure Exact where
  a : Fraction
  b : Fraction
  c : Fraction
  d : Fraction
  deriving Repr

def zero : Exact := ⟨q0, q0, q0, q0⟩
def one : Exact := ⟨q1, q0, q0, q0⟩
def negOne : Exact := ⟨qm1, q0, q0, q0⟩
def imag : Exact := ⟨q0, q0, q1, q0⟩
def negImag : Exact := ⟨q0, q0, qm1, q0⟩
def invSqrtTwo : Exact := ⟨q0, qHalf, q0, q0⟩
def tPhase : Exact := ⟨q0, qHalf, q0, qHalf⟩
def tdgPhase : Exact := ⟨q0, qHalf, q0, qmHalf⟩

def eEq (x y : Exact) : Prop :=
  qEq x.a y.a ∧ qEq x.b y.b ∧ qEq x.c y.c ∧ qEq x.d y.d

def addE (x y : Exact) : Exact :=
  ⟨qAdd x.a y.a, qAdd x.b y.b, qAdd x.c y.c, qAdd x.d y.d⟩

def negE (x : Exact) : Exact :=
  ⟨qNeg x.a, qNeg x.b, qNeg x.c, qNeg x.d⟩

def mulE (x y : Exact) : Exact :=
  ⟨qSub (qAdd (qMul x.a y.a) (qMul q2 (qMul x.b y.b)))
        (qAdd (qMul x.c y.c) (qMul q2 (qMul x.d y.d))),
   qSub (qAdd (qMul x.a y.b) (qMul x.b y.a))
        (qAdd (qMul x.c y.d) (qMul x.d y.c)),
   qAdd (qAdd (qMul x.a y.c) (qMul q2 (qMul x.b y.d)))
        (qAdd (qMul x.c y.a) (qMul q2 (qMul x.d y.b))),
   qAdd (qAdd (qMul x.a y.d) (qMul x.b y.c))
        (qAdd (qMul x.c y.b) (qMul x.d y.a))⟩

structure Mat2 where
  m00 : Exact
  m01 : Exact
  m10 : Exact
  m11 : Exact
  deriving Repr

def mEq (x y : Mat2) : Prop :=
  eEq x.m00 y.m00 ∧ eEq x.m01 y.m01 ∧
  eEq x.m10 y.m10 ∧ eEq x.m11 y.m11

def mulM (x y : Mat2) : Mat2 :=
  ⟨addE (mulE x.m00 y.m00) (mulE x.m01 y.m10),
   addE (mulE x.m00 y.m01) (mulE x.m01 y.m11),
   addE (mulE x.m10 y.m00) (mulE x.m11 y.m10),
   addE (mulE x.m10 y.m01) (mulE x.m11 y.m11)⟩

def I : Mat2 := ⟨one, zero, zero, one⟩
def H : Mat2 := ⟨invSqrtTwo, invSqrtTwo, invSqrtTwo, negE invSqrtTwo⟩
def X : Mat2 := ⟨zero, one, one, zero⟩
def Z : Mat2 := ⟨one, zero, zero, negOne⟩
def S : Mat2 := ⟨one, zero, zero, imag⟩
def SDG : Mat2 := ⟨one, zero, zero, negImag⟩
def T : Mat2 := ⟨one, zero, zero, tPhase⟩
def TDG : Mat2 := ⟨one, zero, zero, tdgPhase⟩

theorem h_squared : mEq (mulM H H) I := by unfold mEq eEq qEq; decide
theorem x_squared : mEq (mulM X X) I := by unfold mEq eEq qEq; decide
theorem z_squared : mEq (mulM Z Z) I := by unfold mEq eEq qEq; decide
theorem s_sdg_inverse : mEq (mulM S SDG) I := by unfold mEq eEq qEq; decide
theorem sdg_s_inverse : mEq (mulM SDG S) I := by unfold mEq eEq qEq; decide
theorem t_tdg_inverse : mEq (mulM T TDG) I := by unfold mEq eEq qEq; decide
theorem tdg_t_inverse : mEq (mulM TDG T) I := by unfold mEq eEq qEq; decide
theorem s_squared : mEq (mulM S S) Z := by unfold mEq eEq qEq; decide
theorem sdg_squared : mEq (mulM SDG SDG) Z := by unfold mEq eEq qEq; decide
theorem t_squared : mEq (mulM T T) S := by unfold mEq eEq qEq; decide
theorem tdg_squared : mEq (mulM TDG TDG) SDG := by unfold mEq eEq qEq; decide
theorem hzh_eq_x : mEq (mulM (mulM H Z) H) X := by unfold mEq eEq qEq; decide
theorem hxh_eq_z : mEq (mulM (mulM H X) H) Z := by unfold mEq eEq qEq; decide

-- The two-bit actions below model computational-basis label permutations.
-- The CZ action carries an explicit Boolean sign bit, toggled on |11⟩.
def cnot01 (v : Bool × Bool) : Bool × Bool :=
  (v.1, if v.1 then !v.2 else v.2)

def cnot10 (v : Bool × Bool) : Bool × Bool :=
  (if v.2 then !v.1 else v.1, v.2)

def swap (v : Bool × Bool) : Bool × Bool := (v.2, v.1)

def cz (v : (Bool × Bool) × Bool) : (Bool × Bool) × Bool :=
  (v.1, if v.1.1 && v.1.2 then !v.2 else v.2)

theorem cnot01_involution (v : Bool × Bool) : cnot01 (cnot01 v) = v := by
  cases v with
  | mk a b => cases a <;> cases b <;> rfl

theorem cnot10_involution (v : Bool × Bool) : cnot10 (cnot10 v) = v := by
  cases v with
  | mk a b => cases a <;> cases b <;> rfl

theorem swap_involution (v : Bool × Bool) : swap (swap v) = v := by
  cases v with
  | mk a b => rfl

theorem cz_involution (v : (Bool × Bool) × Bool) : cz (cz v) = v := by
  cases v with
  | mk pair phase =>
    cases pair with
    | mk a b => cases a <;> cases b <;> cases phase <;> rfl

end PHYSQEDQ
