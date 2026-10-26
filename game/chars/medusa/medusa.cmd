; Commands -------------------------------------------------------------------
; Buttons: x = light punch  y = heavy punch  a = light kick  b = heavy kick
;          z = special button     c = super button        s = taunt
[Remap]
x = x
y = y
z = z
a = a
b = b
c = c
s = s

[Defaults]
command.time = 15
command.buffer.time = 1

[Command]
name = "QCFQCF_x"
command = ~D, DF, F, D, DF, F, x
time = 30

[Command]
name = "QCBQCB_x"
command = ~D, DB, B, D, DB, B, x
time = 30

[Command]
name = "QCFQCF_y"
command = ~D, DF, F, D, DF, F, y
time = 30

[Command]
name = "QCBQCB_y"
command = ~D, DB, B, D, DB, B, y
time = 30

[Command]
name = "QCFQCF_z"
command = ~D, DF, F, D, DF, F, z
time = 30

[Command]
name = "QCBQCB_z"
command = ~D, DB, B, D, DB, B, z
time = 30

[Command]
name = "DP_x"
command = ~F, D, DF, x
time = 15

[Command]
name = "QCF_x"
command = ~D, DF, F, x
time = 15

[Command]
name = "QCB_x"
command = ~D, DB, B, x
time = 15

[Command]
name = "DD_x"
command = ~D, D, x
time = 15

[Command]
name = "DP_y"
command = ~F, D, DF, y
time = 15

[Command]
name = "QCF_y"
command = ~D, DF, F, y
time = 15

[Command]
name = "QCB_y"
command = ~D, DB, B, y
time = 15

[Command]
name = "DD_y"
command = ~D, D, y
time = 15

[Command]
name = "DP_a"
command = ~F, D, DF, a
time = 15

[Command]
name = "QCF_a"
command = ~D, DF, F, a
time = 15

[Command]
name = "QCB_a"
command = ~D, DB, B, a
time = 15

[Command]
name = "DD_a"
command = ~D, D, a
time = 15

[Command]
name = "DP_b"
command = ~F, D, DF, b
time = 15

[Command]
name = "QCF_b"
command = ~D, DF, F, b
time = 15

[Command]
name = "QCB_b"
command = ~D, DB, B, b
time = 15

[Command]
name = "DD_b"
command = ~D, D, b
time = 15

[Command]
name = "FF"
command = F, F
time = 10

[Command]
name = "BB"
command = B, B
time = 10

[Command]
name = "easy_dc"
command = /$D, c
time = 1

[Command]
name = "easy_c"
command = c
time = 1

[Command]
name = "easy_dz"
command = /$D, z
time = 1

[Command]
name = "easy_bz"
command = /$B, z
time = 1

[Command]
name = "easy_fz"
command = /$F, z
time = 1

[Command]
name = "easy_z"
command = z
time = 1

[Command]
name = "recovery"
command = x+y
time = 1

[Command]
name = "throw"
command = /F, y
time = 1

[Command]
name = "throw"
command = /B, y
time = 1

[Command]
name = "x"
command = x
time = 1

[Command]
name = "y"
command = y
time = 1

[Command]
name = "z"
command = z
time = 1

[Command]
name = "a"
command = a
time = 1

[Command]
name = "b"
command = b
time = 1

[Command]
name = "c"
command = c
time = 1

[Command]
name = "s"
command = s
time = 1

[Command]
name = "holdfwd"
command = /$F
time = 1

[Command]
name = "holdback"
command = /$B
time = 1

[Command]
name = "holdup"
command = /$U
time = 1

[Command]
name = "holddown"
command = /$D
time = 1


; ---------------- command -> state ----------------
[Statedef -1]

; CPU (only when AILevel > 0)

[State -1, AI super]
type = ChangeState
triggerall = AILevel > 0
triggerall = RoundState = 2
triggerall = Ctrl
triggerall = StateType != A
trigger1 = Power >= 2000
trigger1 = P2BodyDist X < 260
trigger1 = P2MoveType != A || Random < 300
trigger1 = Random < AILevel * 6
value = 3100

[State -1, AI super]
type = ChangeState
triggerall = AILevel > 0
triggerall = RoundState = 2
triggerall = Ctrl
triggerall = StateType != A
trigger1 = Power >= 1000
trigger1 = P2BodyDist X < 150
trigger1 = P2MoveType != A || Random < 300
trigger1 = Random < AILevel * 6
value = 3000

[State -1, AI zoning]
type = ChangeState
triggerall = AILevel > 0
triggerall = RoundState = 2
triggerall = Ctrl
triggerall = StateType != A
trigger1 = P2BodyDist X > 160
trigger1 = NumProjID(1000) = 0
trigger1 = Random < AILevel * 8
value = 1000

[State -1, AI rush]
type = ChangeState
triggerall = AILevel > 0
triggerall = RoundState = 2
triggerall = Ctrl
triggerall = StateType != A
trigger1 = P2BodyDist X = [40, 180]
trigger1 = P2MoveType != A
trigger1 = Random < AILevel * 5
value = 1100

[State -1, AI throw]
type = ChangeState
triggerall = AILevel > 0
triggerall = RoundState = 2
triggerall = Ctrl
triggerall = StateType != A
trigger1 = P2BodyDist X < 30
trigger1 = P2StateType != A
trigger1 = P2MoveType != H
trigger1 = Random < AILevel * 6
value = 800

[State -1, AI normal 200]
type = ChangeState
triggerall = AILevel > 0
triggerall = RoundState = 2
triggerall = Ctrl
triggerall = StateType != A
trigger1 = P2BodyDist X < 60
trigger1 = P2StateType != L
trigger1 = Random < AILevel * 6
value = 200

[State -1, AI normal 230]
type = ChangeState
triggerall = AILevel > 0
triggerall = RoundState = 2
triggerall = Ctrl
triggerall = StateType != A
trigger1 = P2BodyDist X < 70
trigger1 = P2StateType != L
trigger1 = Random < AILevel * 5
value = 230

[State -1, AI normal 210]
type = ChangeState
triggerall = AILevel > 0
triggerall = RoundState = 2
triggerall = Ctrl
triggerall = StateType != A
trigger1 = P2BodyDist X < 90
trigger1 = P2StateType != L
trigger1 = Random < AILevel * 4
value = 210

[State -1, AI normal 240]
type = ChangeState
triggerall = AILevel > 0
triggerall = RoundState = 2
triggerall = Ctrl
triggerall = StateType != A
trigger1 = P2BodyDist X < 100
trigger1 = P2StateType != L
trigger1 = Random < AILevel * 4
value = 240

[State -1, AI normal 430]
type = ChangeState
triggerall = AILevel > 0
triggerall = RoundState = 2
triggerall = Ctrl
triggerall = StateType != A
trigger1 = P2BodyDist X < 70
trigger1 = P2StateType != L
trigger1 = Random < AILevel * 3
value = 430

[State -1, AI normal 440]
type = ChangeState
triggerall = AILevel > 0
triggerall = RoundState = 2
triggerall = Ctrl
triggerall = StateType != A
trigger1 = P2BodyDist X < 95
trigger1 = P2StateType != L
trigger1 = Random < AILevel * 2
value = 440

[State -1, AI normal 410]
type = ChangeState
triggerall = AILevel > 0
triggerall = RoundState = 2
triggerall = Ctrl
triggerall = StateType != A
trigger1 = P2BodyDist X < 70
trigger1 = P2StateType != L
trigger1 = Random < AILevel * 2
value = 410

[State -1, AI combo]
type = ChangeState
triggerall = AILevel > 0
triggerall = RoundState = 2
trigger1 = StateNo = [200, 249]
trigger1 = MoveHit
trigger1 = AnimTime = 0
trigger1 = Random < AILevel * 100
value = 1100

[State -1, AI anti-air normal]
type = ChangeState
triggerall = AILevel > 0
triggerall = RoundState = 2
triggerall = Ctrl
triggerall = StateType != A
trigger1 = P2StateType = A
trigger1 = P2BodyDist X < 60
trigger1 = Random < AILevel * 20
value = 410

; Player commands

[State -1, strong version flag]
type = VarSet
trigger1 = 1
var(1) = command = "QCF_y" || command = "QCB_y" || command = "DP_y"

[State -1, Spatial collapse (easy)]
type = ChangeState
triggerall = (StateType != A) && (Ctrl || (StateNo = [200, 499] && MoveContact))
triggerall = Power >= 2000
trigger1 = command = "easy_dc"
value = 3100

[State -1, Seven-Coloured Python (easy)]
type = ChangeState
triggerall = (StateType != A) && (Ctrl || (StateNo = [200, 499] && MoveContact))
triggerall = command != "holddown"
triggerall = Power >= 1000
trigger1 = command = "easy_c"
value = 3000

[State -1, Spatial seal (easy)]
type = ChangeState
triggerall = (StateType != A) && (Ctrl || (StateNo = [200, 499] && MoveContact))
trigger1 = command = "easy_dz"
value = 1200

[State -1, Serpent lunge (easy)]
type = ChangeState
triggerall = (StateType != A) && (Ctrl || (StateNo = [200, 499] && MoveContact))
trigger1 = command = "easy_fz"
value = 1100

[State -1, Venomous Flame (easy)]
type = ChangeState
triggerall = (StateType != A) && (Ctrl || (StateNo = [200, 499] && MoveContact))
triggerall = command != "holddown"
trigger1 = command = "easy_z"
value = 1000

[State -1, Spatial collapse]
type = ChangeState
triggerall = (StateType != A) && (Ctrl || (StateNo = [200, 499] && MoveContact))
triggerall = Power >= 2000
trigger1 = command = "QCBQCB_x"
trigger2 = command = "QCBQCB_y"
trigger3 = command = "QCBQCB_z"
value = 3100

[State -1, Seven-Coloured Python]
type = ChangeState
triggerall = (StateType != A) && (Ctrl || (StateNo = [200, 499] && MoveContact))
triggerall = Power >= 1000
trigger1 = command = "QCFQCF_x"
trigger2 = command = "QCFQCF_y"
trigger3 = command = "QCFQCF_z"
value = 3000

[State -1, Spatial seal]
type = ChangeState
triggerall = (StateType != A) && (Ctrl || (StateNo = [200, 499] && MoveContact))
trigger1 = command = "DD_x"
trigger2 = command = "DD_y"
value = 1200

[State -1, Venomous Flame]
type = ChangeState
triggerall = (StateType != A) && (Ctrl || (StateNo = [200, 499] && MoveContact))
trigger1 = command = "QCF_x"
trigger2 = command = "QCF_y"
value = 1000

[State -1, Serpent lunge]
type = ChangeState
triggerall = (StateType != A) && (Ctrl || (StateNo = [200, 499] && MoveContact))
trigger1 = command = "QCB_x"
trigger2 = command = "QCB_y"
value = 1100

[State -1, Throw]
type = ChangeState
trigger1 = command = "throw"
trigger1 = StateType = S
trigger1 = Ctrl
trigger1 = P2BodyDist X < 20
trigger1 = P2StateType != A
trigger1 = P2MoveType != H
value = 800

[State -1, ChangeState]
type = ChangeState
triggerall = StateType = S
triggerall = command != "holddown"
trigger1 = command = "y"
trigger1 = Ctrl
trigger2 = command = "y"
trigger2 = StateNo = [200, 209]
trigger2 = MoveContact
value = 210

[State -1, ChangeState]
type = ChangeState
triggerall = StateType = S
triggerall = command != "holddown"
trigger1 = command = "x"
trigger1 = Ctrl
value = 200

[State -1, ChangeState]
type = ChangeState
triggerall = StateType = S
triggerall = command != "holddown"
trigger1 = command = "b"
trigger1 = Ctrl
trigger2 = command = "b"
trigger2 = StateNo = [200, 239]
trigger2 = MoveContact
value = 240

[State -1, ChangeState]
type = ChangeState
triggerall = StateType = S
triggerall = command != "holddown"
trigger1 = command = "a"
trigger1 = Ctrl
value = 230

[State -1, ChangeState]
type = ChangeState
triggerall = command = "holddown"
triggerall = StateType != A
trigger1 = command = "y"
trigger1 = Ctrl
trigger2 = command = "y"
trigger2 = StateNo = [400, 409]
trigger2 = MoveContact
value = 410

[State -1, ChangeState]
type = ChangeState
triggerall = command = "holddown"
triggerall = StateType != A
trigger1 = command = "x"
trigger1 = Ctrl
value = 400

[State -1, ChangeState]
type = ChangeState
triggerall = command = "holddown"
triggerall = StateType != A
trigger1 = command = "b"
trigger1 = Ctrl
trigger2 = command = "b"
trigger2 = StateNo = [400, 439]
trigger2 = MoveContact
value = 440

[State -1, ChangeState]
type = ChangeState
triggerall = command = "holddown"
triggerall = StateType != A
trigger1 = command = "a"
trigger1 = Ctrl
value = 430

[State -1, ChangeState]
type = ChangeState
triggerall = StateType = A
trigger1 = command = "y"
trigger1 = Ctrl
value = 610

[State -1, ChangeState]
type = ChangeState
triggerall = StateType = A
trigger1 = command = "x"
trigger1 = Ctrl
value = 600

[State -1, ChangeState]
type = ChangeState
triggerall = StateType = A
trigger1 = command = "b"
trigger1 = Ctrl
value = 640

[State -1, ChangeState]
type = ChangeState
triggerall = StateType = A
trigger1 = command = "a"
trigger1 = Ctrl
value = 630

[State -1, Taunt]
type = ChangeState
trigger1 = command = "s"
trigger1 = StateType = S
trigger1 = Ctrl
value = 195

[State -1, Run]
type = ChangeState
trigger1 = command = "FF"
trigger1 = StateType = S
trigger1 = Ctrl
value = 100

[State -1, Hop back]
type = ChangeState
trigger1 = command = "BB"
trigger1 = StateType = S
trigger1 = Ctrl
value = 105
