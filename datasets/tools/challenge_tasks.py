"""Ten compositional challenge tasks used to replace the v0.1 calibration tier."""

from __future__ import annotations


def challenge_tasks(task, var, req, step, test):
    items = []

    items.append(task(
        "C01_X01_voted_bypass_permissive",
        "Voted permissive with qualified bypass and diagnostics",
        "C01", "hard",
        [
            var("Ch1", "BOOL", "Permissive channel 1"), var("Ch2", "BOOL", "Permissive channel 2"),
            var("Ch3", "BOOL", "Permissive channel 3"), var("AutoMode", "BOOL", "Automatic mode selection"),
            var("AutoRequest", "BOOL", "Automatic run request"), var("ManualRequest", "BOOL", "Manual run request"),
            var("BypassRequest", "BOOL", "Maintenance bypass request"), var("BypassPermit", "BOOL", "Independent bypass authorization"),
            var("SafetyOK", "BOOL", "Non-bypassable safety chain"), var("Reset", "BOOL", "Bypass reset"),
        ],
        [
            var("RunPermit", "BOOL", "Final run permission"), var("Degraded", "BOOL", "Run uses disagreement or bypass"),
            var("BypassActive", "BOOL", "Latched qualified bypass"), var("Blocked", "BOOL", "Selected request cannot run"),
        ],
        [
            req("The selected request shall be AutoRequest in automatic mode and ManualRequest otherwise.", "G(selected_request = mux(AutoMode,AutoRequest,ManualRequest))"),
            req("Without bypass, RunPermit requires SafetyOK and at least two TRUE channels.", "G((RunPermit AND !BypassActive) -> (SafetyOK AND vote2of3))", True),
            req("Bypass may latch only in manual mode when BypassRequest, BypassPermit, SafetyOK, and at least one channel are TRUE.", "G(rose(BypassActive) -> (!AutoMode AND BypassRequest AND BypassPermit AND SafetyOK AND any_channel))", True),
            req("Reset may clear BypassActive only when neither automatic nor manual request is active.", "G((Reset AND !AutoRequest AND !ManualRequest) -> !BypassActive)"),
            req("Degraded shall identify a permitted run with channel disagreement or active bypass; Blocked shall identify a selected request without RunPermit.", "G(Degraded = (RunPermit AND ((!unanimous_channels) OR BypassActive))) AND G(Blocked = (selected_request AND !RunPermit))"),
        ],
        """SelectedRequest := (AutoMode AND AutoRequest) OR ((NOT AutoMode) AND ManualRequest);
VoteOK := (Ch1 AND Ch2) OR (Ch1 AND Ch3) OR (Ch2 AND Ch3);
AnyChannel := Ch1 OR Ch2 OR Ch3;
Unanimous := (Ch1 AND Ch2 AND Ch3) OR ((NOT Ch1) AND (NOT Ch2) AND (NOT Ch3));
IF Reset AND (NOT AutoRequest) AND (NOT ManualRequest) THEN
    BypassActive := FALSE;
ELSIF (NOT AutoMode) AND BypassRequest AND BypassPermit AND SafetyOK AND AnyChannel THEN
    BypassActive := TRUE;
END_IF;
RunPermit := SelectedRequest AND SafetyOK AND (VoteOK OR BypassActive);
Degraded := RunPermit AND ((NOT Unanimous) OR BypassActive);
Blocked := SelectedRequest AND (NOT RunPermit);""",
        [test("normal_vote_and_block", ["R1", "R2", "R5"], [
            step({"Ch1": True, "Ch2": True, "Ch3": False, "AutoMode": True, "AutoRequest": True, "ManualRequest": False, "BypassRequest": False, "BypassPermit": False, "SafetyOK": True, "Reset": False}, {"RunPermit": True, "Degraded": True, "BypassActive": False, "Blocked": False}),
            step({"Ch1": True, "Ch2": False, "Ch3": False, "AutoMode": True, "AutoRequest": True, "ManualRequest": False, "BypassRequest": False, "BypassPermit": False, "SafetyOK": True, "Reset": False}, {"RunPermit": False, "Degraded": False, "BypassActive": False, "Blocked": True}),
        ], "Exercise a valid vote and a blocked selected request.")],
        [test("qualified_bypass_lifecycle", ["R2", "R3", "R4", "R5"], [
            step({"Ch1": True, "Ch2": False, "Ch3": False, "AutoMode": False, "AutoRequest": False, "ManualRequest": True, "BypassRequest": True, "BypassPermit": True, "SafetyOK": True, "Reset": False}, {"RunPermit": True, "Degraded": True, "BypassActive": True, "Blocked": False}),
            step({"Ch1": True, "Ch2": False, "Ch3": False, "AutoMode": False, "AutoRequest": False, "ManualRequest": True, "BypassRequest": False, "BypassPermit": False, "SafetyOK": False, "Reset": False}, {"RunPermit": False, "Degraded": False, "BypassActive": True, "Blocked": True}),
            step({"Ch1": False, "Ch2": False, "Ch3": False, "AutoMode": False, "AutoRequest": False, "ManualRequest": False, "BypassRequest": False, "BypassPermit": False, "SafetyOK": True, "Reset": True}, {"RunPermit": False, "Degraded": False, "BypassActive": False, "Blocked": False}),
        ], "Latch a qualified bypass, retain it across safety loss, and clear it only while idle.")],
        internal_vars=["SelectedRequest : BOOL;", "VoteOK : BOOL;", "AnyChannel : BOOL;", "Unanimous : BOOL;"],
        iec_features=["FUNCTION_BLOCK", "BOOL", "IF", "retained state", "2oo3 voting", "priority", "diagnostics"],
        complexity={"retained_state": 1, "transitions": 4, "stateful_blocks": 0, "interactions": 9, "fault_modes": 3, "horizon_scans": 5},
    ))

    items.append(task(
        "C02_X01_restart_inhibit_latch",
        "Mode-selected start latch with restart inhibit",
        "C02", "hard",
        [
            var("AutoMode", "BOOL", "Automatic mode"), var("AutoStart", "BOOL", "Automatic start request"),
            var("ManualStart", "BOOL", "Manual start request"), var("Stop", "BOOL", "High-priority stop"),
            var("Enable", "BOOL", "Controller enable"), var("SafetyOK", "BOOL", "Safety permission"),
            var("Reset", "BOOL", "Restart-inhibit reset"),
        ],
        [var("Running", "BOOL", "Latched running command"), var("RestartRequired", "BOOL", "Manual restart acknowledgement required"), var("RejectedStart", "BOOL", "One-scan rejected-start diagnostic")],
        [
            req("AutoMode shall select AutoStart; manual mode shall select ManualStart.", "G(selected_start = mux(AutoMode,AutoStart,ManualStart))"),
            req("Stop, Enable FALSE, or SafetyOK FALSE shall force Running FALSE with priority over every start.", "G((Stop OR !Enable OR !SafetyOK) -> !Running)", True),
            req("Safety loss while running or while a start is requested shall latch RestartRequired.", "G((!SafetyOK AND (prev(Running) OR selected_start)) -> RestartRequired)", True),
            req("RestartRequired may clear only when Reset is TRUE, SafetyOK and Enable are TRUE, and the selected start is released.", "G((RestartRequired AND !(Reset AND SafetyOK AND Enable AND !selected_start)) -> X(RestartRequired))"),
            req("A start presented while RestartRequired is TRUE shall not run and shall pulse RejectedStart.", "G((RestartRequired AND selected_start) -> (!Running AND RejectedStart))", True),
            req("With all permissions healthy and no restart inhibit, a selected start shall latch Running until a stop condition occurs.", "G((selected_start AND Enable AND SafetyOK AND !Stop AND !RestartRequired) -> Running)"),
        ],
        """SelectedStart := (AutoMode AND AutoStart) OR ((NOT AutoMode) AND ManualStart);
RejectedStart := FALSE;
IF Stop OR (NOT Enable) THEN
    Running := FALSE;
ELSIF NOT SafetyOK THEN
    IF Running OR SelectedStart THEN RestartRequired := TRUE; END_IF;
    Running := FALSE;
ELSIF RestartRequired THEN
    Running := FALSE;
    IF SelectedStart THEN RejectedStart := TRUE; END_IF;
    IF Reset AND Enable AND SafetyOK AND (NOT SelectedStart) THEN RestartRequired := FALSE; END_IF;
ELSIF SelectedStart THEN
    Running := TRUE;
END_IF;""",
        [test("start_latch_and_stop", ["R1", "R2", "R6"], [
            step({"AutoMode": True, "AutoStart": True, "ManualStart": False, "Stop": False, "Enable": True, "SafetyOK": True, "Reset": False}, {"Running": True, "RestartRequired": False, "RejectedStart": False}),
            step({"AutoMode": True, "AutoStart": False, "ManualStart": False, "Stop": False, "Enable": True, "SafetyOK": True, "Reset": False}, {"Running": True, "RestartRequired": False, "RejectedStart": False}),
            step({"AutoMode": True, "AutoStart": True, "ManualStart": False, "Stop": True, "Enable": True, "SafetyOK": True, "Reset": False}, {"Running": False, "RestartRequired": False, "RejectedStart": False}),
        ], "Latch a healthy start and apply simultaneous stop priority.")],
        [test("safety_loss_restart_sequence", ["R2", "R3", "R4", "R5"], [
            step({"AutoMode": False, "AutoStart": False, "ManualStart": True, "Stop": False, "Enable": True, "SafetyOK": True, "Reset": False}, {"Running": True, "RestartRequired": False, "RejectedStart": False}),
            step({"AutoMode": False, "AutoStart": False, "ManualStart": True, "Stop": False, "Enable": True, "SafetyOK": False, "Reset": False}, {"Running": False, "RestartRequired": True, "RejectedStart": False}),
            step({"AutoMode": False, "AutoStart": False, "ManualStart": True, "Stop": False, "Enable": True, "SafetyOK": True, "Reset": True}, {"Running": False, "RestartRequired": True, "RejectedStart": True}),
            step({"AutoMode": False, "AutoStart": False, "ManualStart": False, "Stop": False, "Enable": True, "SafetyOK": True, "Reset": True}, {"Running": False, "RestartRequired": False, "RejectedStart": False}),
        ], "Require release of the selected start before reset.")],
        internal_vars=["SelectedStart : BOOL;"],
        iec_features=["FUNCTION_BLOCK", "BOOL", "IF", "retained latch", "mode selection", "restart inhibit", "priority"],
        complexity={"retained_state": 2, "transitions": 7, "stateful_blocks": 0, "interactions": 8, "fault_modes": 3, "horizon_scans": 7},
    ))

    items.append(task(
        "C03_X01_ventilated_heater_interlock",
        "Ventilated heater startup with proof timeout",
        "C03", "hard",
        [
            var("HeatRequest", "BOOL", "Heat demand"), var("Stop", "BOOL", "Stop command"),
            var("GuardClosed", "BOOL", "Guard safety input"), var("DamperOpen", "BOOL", "Damper proof"),
            var("AirflowOK", "BOOL", "Airflow proof"), var("Reset", "BOOL", "Fault reset"),
        ],
        [
            var("DamperCommand", "BOOL", "Open-damper command"), var("FanCommand", "BOOL", "Ventilation fan command"),
            var("HeaterCommand", "BOOL", "Heater command"), var("Fault", "BOOL", "Latched proof fault"),
            var("State", "INT", "0 idle, 1 proving ventilation, 2 heating"),
        ],
        [
            req("A healthy HeatRequest shall enter ventilation proving and command the damper and fan before the heater.", "G((State=0 AND HeatRequest AND GuardClosed AND !Stop AND !Fault)->X(State=1))"),
            req("HeaterCommand may energize only after DamperOpen and AirflowOK remain TRUE for 300 ms.", "G(HeaterCommand -> continuous(DamperOpen AND AirflowOK,3))", True),
            req("Failure to establish both proofs within 600 ms shall latch Fault and force all commands FALSE.", "G(proof_timeout -> (Fault AND !DamperCommand AND !FanCommand AND !HeaterCommand))", True),
            req("Loss of GuardClosed, DamperOpen, or AirflowOK while heating shall immediately trip and latch Fault.", "G((State=2 AND (!GuardClosed OR !DamperOpen OR !AirflowOK)) -> Fault)", True),
            req("Stop shall return to idle without clearing Fault; Reset clears Fault only while idle with HeatRequest FALSE.", "G(Stop -> State=0) AND G((Reset AND State=0 AND !HeatRequest)->!Fault)"),
            req("HeaterCommand shall never be TRUE unless DamperCommand and FanCommand are both TRUE.", "G(HeaterCommand -> (DamperCommand AND FanCommand))", True),
        ],
        """ProofStable(IN := (State = 1) AND DamperOpen AND AirflowOK, PT := T#300ms);
ProofTimeout(IN := (State = 1) AND ((NOT DamperOpen) OR (NOT AirflowOK)), PT := T#600ms);
IF Stop OR (NOT GuardClosed) THEN
    IF (State = 2) AND (NOT GuardClosed) THEN Fault := TRUE; END_IF;
    State := 0;
ELSIF (State = 2) AND ((NOT DamperOpen) OR (NOT AirflowOK)) THEN
    Fault := TRUE;
    State := 0;
ELSIF ProofTimeout.Q THEN
    Fault := TRUE;
    State := 0;
ELSIF (State = 0) AND HeatRequest AND GuardClosed AND (NOT Fault) THEN
    State := 1;
ELSIF (State = 1) AND ProofStable.Q THEN
    State := 2;
ELSIF (State = 2) AND (NOT HeatRequest) THEN
    State := 0;
END_IF;
IF Reset AND (State = 0) AND (NOT HeatRequest) THEN Fault := FALSE; END_IF;
DamperCommand := ((State = 1) OR (State = 2)) AND (NOT Fault);
FanCommand := ((State = 1) OR (State = 2)) AND (NOT Fault);
HeaterCommand := (State = 2) AND (NOT Fault);""",
        [test("normal_proven_start", ["R1", "R2", "R6"], [
            step({"HeatRequest": True, "Stop": False, "GuardClosed": True, "DamperOpen": True, "AirflowOK": True, "Reset": False}, {"DamperCommand": True, "FanCommand": True, "HeaterCommand": False, "Fault": False, "State": 1}),
            step({"HeatRequest": True, "Stop": False, "GuardClosed": True, "DamperOpen": True, "AirflowOK": True, "Reset": False}, {"DamperCommand": True, "FanCommand": True, "HeaterCommand": True, "Fault": False, "State": 2}, repeat=5, check="last_only"),
        ], "Prove ventilation before enabling heat.")],
        [test("proof_loss_and_qualified_reset", ["R3", "R4", "R5", "R6"], [
            step({"HeatRequest": True, "Stop": False, "GuardClosed": True, "DamperOpen": False, "AirflowOK": False, "Reset": False}, {"DamperCommand": False, "FanCommand": False, "HeaterCommand": False, "Fault": True, "State": 0}, repeat=8, check="last_only"),
            step({"HeatRequest": True, "Stop": True, "GuardClosed": True, "DamperOpen": False, "AirflowOK": False, "Reset": True}, {"DamperCommand": False, "FanCommand": False, "HeaterCommand": False, "Fault": True, "State": 0}),
            step({"HeatRequest": False, "Stop": False, "GuardClosed": True, "DamperOpen": False, "AirflowOK": False, "Reset": True}, {"DamperCommand": False, "FanCommand": False, "HeaterCommand": False, "Fault": False, "State": 0}),
        ], "Time out missing proofs and require idle reset.")],
        internal_vars=["ProofStable : TON;", "ProofTimeout : TON;"],
        iec_features=["FUNCTION_BLOCK", "BOOL", "INT", "TIME", "TON", "retained state", "proof timeout", "interlock"],
        assumptions=["The runtime scan period is 100 ms.", "Proof inputs are sampled at scan start.", "Each test starts from a fresh function-block instance."],
        complexity={"retained_state": 3, "transitions": 9, "stateful_blocks": 2, "interactions": 8, "fault_modes": 3, "horizon_scans": 12},
    ))

    items.append(task(
        "C04_X01_dual_event_saturating_recorder",
        "Qualified dual-edge recorder with saturation and re-arm",
        "C04", "hard",
        [
            var("EventA", "BOOL", "Event channel A"), var("EventB", "BOOL", "Event channel B"),
            var("Qualify", "BOOL", "Event qualification"), var("Inhibit", "BOOL", "Event inhibit"),
            var("Reset", "BOOL", "Qualified reset"), var("MaxCount", "INT", "Saturation count"),
        ],
        [
            var("PulseA", "BOOL", "Accepted A pulse"), var("PulseB", "BOOL", "Accepted B pulse"),
            var("Count", "INT", "Accepted event count"), var("Locked", "BOOL", "Saturation lockout"),
            var("LastSource", "INT", "0 none, 1 A, 2 B"),
        ],
        [
            req("Only a qualified, non-inhibited rising edge observed while not previously locked may be accepted.", "G((PulseA OR PulseB) -> (Qualify AND !Inhibit AND !prev(Locked)))", True),
            req("Simultaneous eligible edges shall accept A only.", "G((rose(EventA) AND rose(EventB) AND eligible) -> (PulseA AND !PulseB))", True),
            req("Each accepted event increments Count once and records LastSource.", "G((PulseA OR PulseB) -> (Count=prev(Count)+1))"),
            req("Except for a qualified reset scan, Count shall saturate at MaxCount and latch Locked; MaxCount less than or equal to zero locks without counting.", "G(((Count>=MaxCount OR MaxCount<=0) AND !(Reset AND !EventA AND !EventB))->Locked)", True),
            req("A held-high event shall not retrigger until observed low and then rising again.", "G((EventA AND prev(EventA))->!PulseA) AND G((EventB AND prev(EventB))->!PulseB)"),
            req("Reset clears Count, Locked, and LastSource only while both events are low.", "G((Reset AND !EventA AND !EventB)->(Count=0 AND !Locked AND LastSource=0))"),
        ],
        """PulseA := FALSE;
PulseB := FALSE;
IF Reset AND (NOT EventA) AND (NOT EventB) THEN
    Count := 0;
    Locked := FALSE;
    LastSource := 0;
ELSIF MaxCount <= 0 THEN
    Locked := TRUE;
ELSIF Qualify AND (NOT Inhibit) AND (NOT Locked) THEN
    IF EventA AND (NOT PrevA) THEN
        PulseA := TRUE;
        Count := Count + 1;
        LastSource := 1;
    ELSIF EventB AND (NOT PrevB) THEN
        PulseB := TRUE;
        Count := Count + 1;
        LastSource := 2;
    END_IF;
    IF Count >= MaxCount THEN Count := MaxCount; Locked := TRUE; END_IF;
END_IF;
PrevA := EventA;
PrevB := EventB;""",
        [test("priority_edge_and_rearm", ["R1", "R2", "R3", "R5"], [
            step({"EventA": False, "EventB": False, "Qualify": True, "Inhibit": False, "Reset": False, "MaxCount": 3}, {"PulseA": False, "PulseB": False, "Count": 0, "Locked": False, "LastSource": 0}),
            step({"EventA": True, "EventB": True, "Qualify": True, "Inhibit": False, "Reset": False, "MaxCount": 3}, {"PulseA": True, "PulseB": False, "Count": 1, "Locked": False, "LastSource": 1}),
            step({"EventA": True, "EventB": True, "Qualify": True, "Inhibit": False, "Reset": False, "MaxCount": 3}, {"PulseA": False, "PulseB": False, "Count": 1, "Locked": False, "LastSource": 1}),
        ], "Accept A on a tie and reject held-high retriggers.")],
        [test("saturation_and_qualified_reset", ["R3", "R4", "R6"], [
            step({"EventA": False, "EventB": True, "Qualify": True, "Inhibit": False, "Reset": False, "MaxCount": 2}, {"PulseA": False, "PulseB": True, "Count": 1, "Locked": False, "LastSource": 2}),
            step({"EventA": False, "EventB": False, "Qualify": True, "Inhibit": False, "Reset": False, "MaxCount": 2}, {"PulseA": False, "PulseB": False, "Count": 1, "Locked": False, "LastSource": 2}),
            step({"EventA": True, "EventB": False, "Qualify": True, "Inhibit": False, "Reset": False, "MaxCount": 2}, {"PulseA": True, "PulseB": False, "Count": 2, "Locked": True, "LastSource": 1}),
            step({"EventA": False, "EventB": False, "Qualify": True, "Inhibit": False, "Reset": True, "MaxCount": 2}, {"PulseA": False, "PulseB": False, "Count": 0, "Locked": False, "LastSource": 0}),
        ], "Saturate at the configured boundary and reset only with both inputs low.")],
        internal_vars=["PrevA : BOOL;", "PrevB : BOOL;"],
        iec_features=["FUNCTION_BLOCK", "BOOL", "INT", "IF", "edge memory", "priority", "saturation", "qualified reset"],
        complexity={"retained_state": 5, "transitions": 9, "stateful_blocks": 0, "interactions": 8, "fault_modes": 2, "horizon_scans": 9},
    ))

    items.append(task(
        "C05_X01_pre_lube_motor_lifecycle",
        "Pre-lube motor lifecycle with feedback fault and cooldown",
        "C05", "hard",
        [
            var("Start", "BOOL", "Start request"), var("Stop", "BOOL", "Stop request"),
            var("Permit", "BOOL", "Safety permission"), var("OilPressure", "BOOL", "Lubrication pressure proof"),
            var("MotorFeedback", "BOOL", "Motor running feedback"), var("Reset", "BOOL", "Fault reset"),
        ],
        [
            var("LubePump", "BOOL", "Lubrication pump command"), var("MotorCommand", "BOOL", "Motor command"),
            var("Cooldown", "BOOL", "Cooldown state indication"), var("Fault", "BOOL", "Latched startup or oil fault"),
            var("State", "INT", "0 idle, 1 pre-lube, 2 feedback proving, 3 running, 4 cooldown"),
        ],
        [
            req("A permitted start shall enter pre-lube with LubePump TRUE and MotorCommand FALSE.", "G((State=0 AND Start AND Permit AND !Stop AND !Fault)->X(State=1))"),
            req("MotorCommand may start only after OilPressure remains TRUE for 300 ms.", "G(MotorCommand -> continuous(OilPressure,3))", True),
            req("Failure to receive MotorFeedback within 400 ms of MotorCommand shall latch Fault and enter cooldown.", "G(feedback_timeout -> (Fault AND State=4 AND !MotorCommand))", True),
            req("OilPressure loss while running shall immediately stop the motor, latch Fault, and enter cooldown.", "G((State=3 AND !OilPressure)->(Fault AND !MotorCommand AND State=4))", True),
            req("Stop or Permit loss shall stop MotorCommand and enter a 300 ms cooldown with LubePump remaining TRUE.", "G(((Stop OR !Permit) AND prev(State)>0)->(State=4 AND !MotorCommand))", True),
            req("Reset clears Fault only in idle with Start FALSE; cooldown completion returns idle without clearing Fault.", "G((Reset AND State=0 AND !Start)->!Fault)"),
        ],
        """PreLube(IN := (State = 1) AND OilPressure, PT := T#300ms);
FeedbackWait(IN := (State = 2) AND (NOT MotorFeedback), PT := T#400ms);
CoolTimer(IN := (State = 4), PT := T#300ms);
IF (State <> 0) AND (State <> 4) AND (Stop OR (NOT Permit)) THEN
    State := 4;
ELSIF (State = 3) AND (NOT OilPressure) THEN
    Fault := TRUE;
    State := 4;
ELSIF (State = 2) AND FeedbackWait.Q THEN
    Fault := TRUE;
    State := 4;
ELSIF (State = 0) AND Start AND Permit AND (NOT Stop) AND (NOT Fault) THEN
    State := 1;
ELSIF (State = 1) AND PreLube.Q THEN
    State := 2;
ELSIF (State = 2) AND MotorFeedback THEN
    IF OilPressure THEN
        State := 3;
    ELSE
        Fault := TRUE;
        State := 4;
    END_IF;
ELSIF (State = 4) AND CoolTimer.Q THEN
    State := 0;
END_IF;
IF Reset AND (State = 0) AND (NOT Start) THEN Fault := FALSE; END_IF;
LubePump := ((State = 1) OR (State = 2) OR (State = 3) OR (State = 4));
MotorCommand := ((State = 2) OR (State = 3)) AND (NOT Fault);
Cooldown := (State = 4);""",
        [test("healthy_lifecycle", ["R1", "R2"], [
            step({"Start": True, "Stop": False, "Permit": True, "OilPressure": True, "MotorFeedback": False, "Reset": False}, {"LubePump": True, "MotorCommand": False, "Cooldown": False, "Fault": False, "State": 1}),
            step({"Start": True, "Stop": False, "Permit": True, "OilPressure": True, "MotorFeedback": False, "Reset": False}, {"LubePump": True, "MotorCommand": True, "Cooldown": False, "Fault": False, "State": 2}, repeat=5, check="last_only"),
            step({"Start": True, "Stop": False, "Permit": True, "OilPressure": True, "MotorFeedback": True, "Reset": False}, {"LubePump": True, "MotorCommand": True, "Cooldown": False, "Fault": False, "State": 3}),
        ], "Complete pre-lube and prove motor feedback.")],
        [test("feedback_timeout_cooldown_reset", ["R3", "R5", "R6"], [
            step({"Start": True, "Stop": False, "Permit": True, "OilPressure": True, "MotorFeedback": False, "Reset": False}, {"LubePump": True, "MotorCommand": False, "Cooldown": True, "Fault": True, "State": 4}, repeat=10, check="last_only"),
            step({"Start": False, "Stop": False, "Permit": True, "OilPressure": False, "MotorFeedback": False, "Reset": False}, {"LubePump": False, "MotorCommand": False, "Cooldown": False, "Fault": True, "State": 0}, repeat=5, check="last_only"),
            step({"Start": False, "Stop": False, "Permit": True, "OilPressure": False, "MotorFeedback": False, "Reset": True}, {"LubePump": False, "MotorCommand": False, "Cooldown": False, "Fault": False, "State": 0}),
        ], "Time out feedback, complete cooldown, and reset only in idle."),
        test("running_oil_loss", ["R4", "R5"], [
            step({"Start": True, "Stop": False, "Permit": True, "OilPressure": True, "MotorFeedback": False, "Reset": False}, {"LubePump": True, "MotorCommand": False, "Cooldown": False, "Fault": False, "State": 1}),
            step({"Start": True, "Stop": False, "Permit": True, "OilPressure": True, "MotorFeedback": False, "Reset": False}, {"LubePump": True, "MotorCommand": True, "Cooldown": False, "Fault": False, "State": 2}, repeat=5, check="last_only"),
            step({"Start": True, "Stop": False, "Permit": True, "OilPressure": True, "MotorFeedback": True, "Reset": False}, {"LubePump": True, "MotorCommand": True, "Cooldown": False, "Fault": False, "State": 3}),
            step({"Start": True, "Stop": False, "Permit": True, "OilPressure": False, "MotorFeedback": True, "Reset": False}, {"LubePump": True, "MotorCommand": False, "Cooldown": True, "Fault": True, "State": 4}),
        ], "Trip immediately on lubrication proof loss while running.")],
        internal_vars=["PreLube : TON;", "FeedbackWait : TON;", "CoolTimer : TON;"],
        iec_features=["FUNCTION_BLOCK", "BOOL", "INT", "TIME", "TON", "state machine", "feedback timeout", "cooldown"],
        assumptions=["The runtime scan period is 100 ms.", "Start may remain TRUE through startup.", "Each test starts from a fresh function-block instance."],
        complexity={"retained_state": 4, "transitions": 11, "stateful_blocks": 3, "interactions": 9, "fault_modes": 4, "horizon_scans": 16},
    ))

    items.append(task(
        "C06_X01_batch_quality_lockout",
        "Edge-counted batch with consecutive-reject lockout",
        "C06", "hard",
        [
            var("ItemPulse", "BOOL", "Item completion signal"), var("Rejected", "BOOL", "Current item rejection flag"),
            var("Stop", "BOOL", "Batch stop"), var("Reset", "BOOL", "Qualified reset"),
            var("Target", "INT", "Required accepted items"), var("RejectLimit", "INT", "Consecutive rejects causing lockout"),
        ],
        [
            var("AcceptedCount", "INT", "Accepted item count"), var("RejectCount", "INT", "Total reject count"),
            var("ConsecutiveRejects", "INT", "Current consecutive reject count"), var("Complete", "BOOL", "Accepted target reached"),
            var("LockedOut", "BOOL", "Consecutive reject lockout"),
        ],
        [
            req("Only a rising ItemPulse while not stopped, complete, or locked shall count one item.", "G(count_change -> (rose(ItemPulse) AND !Stop AND !prev(Complete) AND !prev(LockedOut)))"),
            req("An accepted item increments AcceptedCount and clears ConsecutiveRejects; a rejected item increments both reject counters.", "G(accepted_edge -> (AcceptedCount=prev(AcceptedCount)+1 AND ConsecutiveRejects=0)) AND G(rejected_edge -> (RejectCount=prev(RejectCount)+1 AND ConsecutiveRejects=prev(ConsecutiveRejects)+1))"),
            req("Complete shall latch when AcceptedCount reaches positive Target and no later item may change counts.", "G(Complete -> X(Complete))"),
            req("Except for a qualified reset scan, RejectLimit less than or equal to zero, or reaching RejectLimit consecutive rejects, shall latch LockedOut.", "G(((RejectLimit<=0 OR ConsecutiveRejects>=RejectLimit) AND !(Reset AND Stop AND !ItemPulse))->LockedOut)", True),
            req("Stop has priority over ItemPulse and prevents every count change.", "G(Stop -> stable(AcceptedCount,RejectCount,ConsecutiveRejects))", True),
            req("Reset clears all state only while Stop is TRUE and ItemPulse is FALSE.", "G((Reset AND Stop AND !ItemPulse)->(AcceptedCount=0 AND RejectCount=0 AND ConsecutiveRejects=0 AND !Complete AND !LockedOut))"),
        ],
        """IF Reset AND Stop AND (NOT ItemPulse) THEN
    AcceptedCount := 0;
    RejectCount := 0;
    ConsecutiveRejects := 0;
    Complete := FALSE;
    LockedOut := FALSE;
ELSIF RejectLimit <= 0 THEN
    LockedOut := TRUE;
ELSIF ItemPulse AND (NOT PrevItem) AND (NOT Stop) AND (NOT Complete) AND (NOT LockedOut) THEN
    IF Rejected THEN
        RejectCount := RejectCount + 1;
        ConsecutiveRejects := ConsecutiveRejects + 1;
        IF ConsecutiveRejects >= RejectLimit THEN LockedOut := TRUE; END_IF;
    ELSE
        AcceptedCount := AcceptedCount + 1;
        ConsecutiveRejects := 0;
        IF (Target > 0) AND (AcceptedCount >= Target) THEN Complete := TRUE; END_IF;
    END_IF;
END_IF;
PrevItem := ItemPulse;""",
        [test("mixed_batch_edges", ["R1", "R2", "R3"], [
            step({"ItemPulse": True, "Rejected": False, "Stop": False, "Reset": False, "Target": 2, "RejectLimit": 2}, {"AcceptedCount": 1, "RejectCount": 0, "ConsecutiveRejects": 0, "Complete": False, "LockedOut": False}),
            step({"ItemPulse": False, "Rejected": False, "Stop": False, "Reset": False, "Target": 2, "RejectLimit": 2}, {"AcceptedCount": 1, "RejectCount": 0, "ConsecutiveRejects": 0, "Complete": False, "LockedOut": False}),
            step({"ItemPulse": True, "Rejected": False, "Stop": False, "Reset": False, "Target": 2, "RejectLimit": 2}, {"AcceptedCount": 2, "RejectCount": 0, "ConsecutiveRejects": 0, "Complete": True, "LockedOut": False}),
        ], "Count only rising edges and latch completion at Target.")],
        [test("reject_lockout_stop_reset", ["R2", "R4", "R5", "R6"], [
            step({"ItemPulse": True, "Rejected": True, "Stop": False, "Reset": False, "Target": 5, "RejectLimit": 2}, {"AcceptedCount": 0, "RejectCount": 1, "ConsecutiveRejects": 1, "Complete": False, "LockedOut": False}),
            step({"ItemPulse": False, "Rejected": True, "Stop": False, "Reset": False, "Target": 5, "RejectLimit": 2}, {"AcceptedCount": 0, "RejectCount": 1, "ConsecutiveRejects": 1, "Complete": False, "LockedOut": False}),
            step({"ItemPulse": True, "Rejected": True, "Stop": False, "Reset": False, "Target": 5, "RejectLimit": 2}, {"AcceptedCount": 0, "RejectCount": 2, "ConsecutiveRejects": 2, "Complete": False, "LockedOut": True}),
            step({"ItemPulse": False, "Rejected": False, "Stop": True, "Reset": True, "Target": 5, "RejectLimit": 2}, {"AcceptedCount": 0, "RejectCount": 0, "ConsecutiveRejects": 0, "Complete": False, "LockedOut": False}),
        ], "Latch after consecutive rejects and require stopped reset.")],
        internal_vars=["PrevItem : BOOL;"],
        iec_features=["FUNCTION_BLOCK", "BOOL", "INT", "edge memory", "saturating state", "lockout", "qualified reset"],
        complexity={"retained_state": 6, "transitions": 10, "stateful_blocks": 0, "interactions": 9, "fault_modes": 3, "horizon_scans": 12},
    ))

    items.append(task(
        "C07_X01_plausible_rate_limited_fusion",
        "Redundant sensor fusion with plausibility and rate trip",
        "C07", "hard",
        [
            var("SensorA", "REAL", "Sensor A value"), var("SensorB", "REAL", "Sensor B value"),
            var("ValidA", "BOOL", "Sensor A validity"), var("ValidB", "BOOL", "Sensor B validity"),
            var("Enable", "BOOL", "Fusion enable"), var("MaxDifference", "REAL", "Maximum pair disagreement"),
            var("MaxRate", "REAL", "Maximum accepted per-scan change"), var("Reset", "BOOL", "Rate-trip reset"),
        ],
        [
            var("ProcessValue", "REAL", "Accepted fused value"), var("ValidOutput", "BOOL", "ProcessValue is usable"),
            var("Degraded", "BOOL", "Only one sensor is used"), var("Disagree", "BOOL", "Both valid sensors disagree"),
            var("RateTrip", "BOOL", "Latched excessive rate change"),
        ],
        [
            req("When both sensors are valid and their absolute difference is at most MaxDifference, the candidate value is their average.", "G(both_plausible -> candidate=(SensorA+SensorB)/2)"),
            req("When exactly one sensor is valid, the candidate is that sensor and Degraded is TRUE.", "G(exactly_one_valid -> Degraded)"),
            req("When both valid sensors differ by more than MaxDifference, Disagree is TRUE and ValidOutput is FALSE.", "G(disagreement -> (Disagree AND !ValidOutput))", True),
            req("After initialization, an otherwise valid candidate changing by more than MaxRate shall latch RateTrip and shall not replace ProcessValue.", "G((Ready AND candidate_valid AND abs(candidate-prev(ProcessValue))>MaxRate)->(RateTrip AND ProcessValue=prev(ProcessValue)))", True),
            req("RateTrip or Enable FALSE shall force ValidOutput FALSE; Reset clears RateTrip only while disabled.", "G((RateTrip OR !Enable)->!ValidOutput) AND G((Reset AND !Enable)->!RateTrip)", True),
            req("At equality boundaries for MaxDifference and MaxRate, the candidate remains acceptable.", "G(abs_difference=MaxDifference -> !Disagree)"),
        ],
        """CandidateValid := FALSE;
Degraded := FALSE;
Disagree := FALSE;
IF Enable THEN
    IF ValidA AND ValidB THEN
        IF ABS(SensorA - SensorB) <= MaxDifference THEN
            Candidate := (SensorA + SensorB) / 2.0;
            CandidateValid := TRUE;
        ELSE
            Disagree := TRUE;
        END_IF;
    ELSIF ValidA THEN
        Candidate := SensorA; CandidateValid := TRUE; Degraded := TRUE;
    ELSIF ValidB THEN
        Candidate := SensorB; CandidateValid := TRUE; Degraded := TRUE;
    END_IF;
    IF CandidateValid AND (NOT RateTrip) THEN
        IF Ready AND (ABS(Candidate - ProcessValue) > MaxRate) THEN
            RateTrip := TRUE;
        ELSE
            ProcessValue := Candidate;
            Ready := TRUE;
        END_IF;
    END_IF;
ELSE
    Ready := FALSE;
    IF Reset THEN RateTrip := FALSE; END_IF;
END_IF;
ValidOutput := Enable AND CandidateValid AND (NOT RateTrip);
IF RateTrip THEN Degraded := FALSE; END_IF;""",
        [test("average_degraded_and_equality", ["R1", "R2", "R6"], [
            step({"SensorA": 10.0, "SensorB": 12.0, "ValidA": True, "ValidB": True, "Enable": True, "MaxDifference": 2.0, "MaxRate": 5.0, "Reset": False}, {"ProcessValue": 11.0, "ValidOutput": True, "Degraded": False, "Disagree": False, "RateTrip": False}),
            step({"SensorA": 12.0, "SensorB": 50.0, "ValidA": True, "ValidB": False, "Enable": True, "MaxDifference": 2.0, "MaxRate": 5.0, "Reset": False}, {"ProcessValue": 12.0, "ValidOutput": True, "Degraded": True, "Disagree": False, "RateTrip": False}),
        ], "Accept disagreement equality and then fall back to one valid sensor.")],
        [test("disagreement_rate_trip_reset", ["R3", "R4", "R5"], [
            step({"SensorA": 10.0, "SensorB": 10.0, "ValidA": True, "ValidB": True, "Enable": True, "MaxDifference": 1.0, "MaxRate": 2.0, "Reset": False}, {"ProcessValue": 10.0, "ValidOutput": True, "Degraded": False, "Disagree": False, "RateTrip": False}),
            step({"SensorA": 13.0, "SensorB": 13.0, "ValidA": True, "ValidB": True, "Enable": True, "MaxDifference": 1.0, "MaxRate": 2.0, "Reset": False}, {"ProcessValue": 10.0, "ValidOutput": False, "Degraded": False, "Disagree": False, "RateTrip": True}),
            step({"SensorA": 10.0, "SensorB": 15.0, "ValidA": True, "ValidB": True, "Enable": True, "MaxDifference": 1.0, "MaxRate": 2.0, "Reset": True}, {"ProcessValue": 10.0, "ValidOutput": False, "Degraded": False, "Disagree": True, "RateTrip": True}),
            step({"SensorA": 10.0, "SensorB": 10.0, "ValidA": True, "ValidB": True, "Enable": False, "MaxDifference": 1.0, "MaxRate": 2.0, "Reset": True}, {"ProcessValue": 10.0, "ValidOutput": False, "Degraded": False, "Disagree": False, "RateTrip": False}),
        ], "Latch a rate trip, preserve disagreement diagnostics, and reset only disabled.")],
        internal_vars=["Candidate : REAL;", "CandidateValid : BOOL;", "Ready : BOOL;"],
        iec_features=["FUNCTION_BLOCK", "BOOL", "REAL", "ABS", "retained state", "sensor fusion", "boundary", "latched trip"],
        complexity={"retained_state": 3, "transitions": 8, "stateful_blocks": 0, "interactions": 10, "fault_modes": 4, "horizon_scans": 8},
    ))

    items.append(task(
        "C08_X01_paused_three_stage_timeout",
        "Paused three-stage sequence with abort and per-stage timeout",
        "C08", "hard",
        [
            var("Start", "BOOL", "Start sequence"), var("Stage1Done", "BOOL", "Stage 1 completion"),
            var("Stage2Done", "BOOL", "Stage 2 completion"), var("Stage3Done", "BOOL", "Stage 3 completion"),
            var("Pause", "BOOL", "Pause request"), var("Abort", "BOOL", "Abort request"),
            var("Reset", "BOOL", "Fault reset"),
        ],
        [
            var("Actuator1", "BOOL", "Stage 1 actuator"), var("Actuator2", "BOOL", "Stage 2 actuator"),
            var("Actuator3", "BOOL", "Stage 3 actuator"), var("Paused", "BOOL", "Sequence paused"),
            var("Complete", "BOOL", "One-scan completion pulse"), var("Fault", "BOOL", "Abort or timeout lockout"),
            var("State", "INT", "0 idle, 1 stage1, 2 stage2, 3 stage3"),
        ],
        [
            req("Start in idle shall enter stage 1; each matching Done input advances exactly one stage, and Stage3Done returns idle with a one-scan Complete pulse.", "G(stage_done -> next_stage)"),
            req("Pause shall retain State while forcing every actuator FALSE; Done inputs while paused shall not advance.", "G(Pause -> (!Actuator1 AND !Actuator2 AND !Actuator3 AND X(State)=State))", True),
            req("The active stage shall time out after 500 ms of unpaused execution and latch Fault.", "G(stage_timeout -> Fault)", True),
            req("Abort shall immediately return idle, force safe outputs, and latch Fault.", "G(Abort -> (State=0 AND Fault AND !Actuator1 AND !Actuator2 AND !Actuator3))", True),
            req("Reset clears Fault only in idle while Start, Abort, and every Done input are FALSE.", "G(qualified_reset -> !Fault)"),
            req("At most one actuator may be TRUE, and Complete shall never coincide with an actuator.", "G(at_most_one(Actuator1,Actuator2,Actuator3)) AND G(Complete -> (!Actuator1 AND !Actuator2 AND !Actuator3))", True),
        ],
        """Complete := FALSE;
StageTimer(IN := (State > 0) AND (NOT Pause), PT := T#500ms);
IF Abort THEN
    State := 0;
    Fault := TRUE;
ELSIF StageTimer.Q THEN
    State := 0;
    Fault := TRUE;
ELSIF (State = 0) AND Reset AND (NOT Start) AND (NOT Abort) AND (NOT Stage1Done) AND (NOT Stage2Done) AND (NOT Stage3Done) THEN
    Fault := FALSE;
ELSIF NOT Fault THEN
    IF (State = 0) AND Start THEN
        State := 1;
    ELSIF NOT Pause THEN
        CASE State OF
            1: IF Stage1Done THEN State := 2; END_IF;
            2: IF Stage2Done THEN State := 3; END_IF;
            3: IF Stage3Done THEN State := 0; Complete := TRUE; END_IF;
            ELSE State := 0;
        END_CASE;
    END_IF;
END_IF;
Paused := (State > 0) AND Pause AND (NOT Fault);
Actuator1 := (State = 1) AND (NOT Pause) AND (NOT Fault);
Actuator2 := (State = 2) AND (NOT Pause) AND (NOT Fault);
Actuator3 := (State = 3) AND (NOT Pause) AND (NOT Fault);""",
        [test("pause_resume_progress", ["R1", "R2", "R6"], [
            step({"Start": True, "Stage1Done": False, "Stage2Done": False, "Stage3Done": False, "Pause": False, "Abort": False, "Reset": False}, {"Actuator1": True, "Actuator2": False, "Actuator3": False, "Paused": False, "Complete": False, "Fault": False, "State": 1}),
            step({"Start": False, "Stage1Done": True, "Stage2Done": False, "Stage3Done": False, "Pause": True, "Abort": False, "Reset": False}, {"Actuator1": False, "Actuator2": False, "Actuator3": False, "Paused": True, "Complete": False, "Fault": False, "State": 1}),
            step({"Start": False, "Stage1Done": True, "Stage2Done": False, "Stage3Done": False, "Pause": False, "Abort": False, "Reset": False}, {"Actuator1": False, "Actuator2": True, "Actuator3": False, "Paused": False, "Complete": False, "Fault": False, "State": 2}),
        ], "Pause with a done input asserted, then consume it only after resume.")],
        [test("timeout_abort_and_reset", ["R3", "R4", "R5", "R6"], [
            step({"Start": True, "Stage1Done": False, "Stage2Done": False, "Stage3Done": False, "Pause": False, "Abort": False, "Reset": False}, {"Actuator1": False, "Actuator2": False, "Actuator3": False, "Paused": False, "Complete": False, "Fault": True, "State": 0}, repeat=8, check="last_only"),
            step({"Start": False, "Stage1Done": False, "Stage2Done": False, "Stage3Done": False, "Pause": False, "Abort": False, "Reset": True}, {"Actuator1": False, "Actuator2": False, "Actuator3": False, "Paused": False, "Complete": False, "Fault": False, "State": 0}),
            step({"Start": True, "Stage1Done": False, "Stage2Done": False, "Stage3Done": False, "Pause": False, "Abort": True, "Reset": False}, {"Actuator1": False, "Actuator2": False, "Actuator3": False, "Paused": False, "Complete": False, "Fault": True, "State": 0}),
        ], "Time out, reset, and then verify abort priority.")],
        internal_vars=["StageTimer : TON;"],
        iec_features=["FUNCTION_BLOCK", "BOOL", "INT", "TIME", "TON", "CASE", "state machine", "pause", "abort", "timeout"],
        assumptions=["The runtime scan period is 100 ms.", "Pausing resets rather than accumulates the stage timeout.", "Each test starts from a fresh function-block instance."],
        complexity={"retained_state": 4, "transitions": 12, "stateful_blocks": 1, "interactions": 10, "fault_modes": 3, "horizon_scans": 15},
    ))

    items.append(task(
        "C09_X01_shelved_alarm_lifecycle",
        "Delayed warning, immediate trip, shelving, acknowledgement, and reset",
        "C09", "hard",
        [
            var("WarningCondition", "BOOL", "Warning condition"), var("TripCondition", "BOOL", "Trip condition"),
            var("Enable", "BOOL", "Alarm enable"), var("Shelve", "BOOL", "Warning shelving request"),
            var("Acknowledge", "BOOL", "Operator acknowledgement"), var("Reset", "BOOL", "Qualified trip reset"),
        ],
        [
            var("Warning", "BOOL", "Delayed warning indication"), var("Trip", "BOOL", "Latched trip"),
            var("Unacked", "BOOL", "Active alarm not acknowledged"), var("Shelved", "BOOL", "Warning display is shelved"),
            var("LockedOut", "BOOL", "Trip lockout"),
        ],
        [
            req("An enabled WarningCondition shall become Warning after 300 ms unless shelved or a trip is active.", "G(Warning -> continuous(Enable AND WarningCondition AND !Shelved AND !Trip,3))"),
            req("Shelve may suppress only warnings; TripCondition shall latch Trip and LockedOut immediately regardless of Shelve.", "G((Enable AND TripCondition)->(Trip AND LockedOut))", True),
            req("Every newly displayed Warning or Trip shall set Unacked; Acknowledge clears Unacked without clearing active alarms.", "G(new_alarm -> Unacked)"),
            req("Shelved follows Shelve only while no trip is active; a trip cancels Shelved.", "G(Trip -> !Shelved)", True),
            req("Enable FALSE shall suppress Warning but shall not clear Trip or LockedOut.", "G(!Enable -> !Warning)"),
            req("Reset clears Trip and LockedOut only when disabled and both conditions are FALSE.", "G((Reset AND !Enable AND !WarningCondition AND !TripCondition)->(!Trip AND !LockedOut))", True),
        ],
        """WarningDelay(IN := Enable AND WarningCondition AND (NOT Shelved) AND (NOT Trip), PT := T#300ms);
NewWarning := WarningDelay.Q AND (NOT Warning);
IF Enable AND TripCondition THEN
    Trip := TRUE;
    LockedOut := TRUE;
    Shelved := FALSE;
    Unacked := TRUE;
ELSE
    IF Shelve AND (NOT Trip) THEN Shelved := TRUE;
    ELSIF NOT Shelve THEN Shelved := FALSE;
    END_IF;
    IF NewWarning THEN Unacked := TRUE; END_IF;
END_IF;
Warning := WarningDelay.Q AND Enable AND (NOT Shelved) AND (NOT Trip);
IF Acknowledge THEN Unacked := FALSE; END_IF;
IF Reset AND (NOT Enable) AND (NOT WarningCondition) AND (NOT TripCondition) THEN
    Trip := FALSE;
    LockedOut := FALSE;
    Unacked := FALSE;
    Shelved := FALSE;
END_IF;""",
        [test("delayed_warning_ack_shelve", ["R1", "R3", "R4"], [
            step({"WarningCondition": True, "TripCondition": False, "Enable": True, "Shelve": False, "Acknowledge": False, "Reset": False}, {"Warning": True, "Trip": False, "Unacked": True, "Shelved": False, "LockedOut": False}, repeat=5, check="last_only"),
            step({"WarningCondition": True, "TripCondition": False, "Enable": True, "Shelve": False, "Acknowledge": True, "Reset": False}, {"Warning": True, "Trip": False, "Unacked": False, "Shelved": False, "LockedOut": False}),
            step({"WarningCondition": True, "TripCondition": False, "Enable": True, "Shelve": True, "Acknowledge": False, "Reset": False}, {"Warning": False, "Trip": False, "Unacked": False, "Shelved": True, "LockedOut": False}),
        ], "Delay, acknowledge, and shelve a warning.")],
        [test("trip_override_and_qualified_reset", ["R2", "R3", "R4", "R5", "R6"], [
            step({"WarningCondition": True, "TripCondition": True, "Enable": True, "Shelve": True, "Acknowledge": False, "Reset": False}, {"Warning": False, "Trip": True, "Unacked": True, "Shelved": False, "LockedOut": True}),
            step({"WarningCondition": False, "TripCondition": False, "Enable": True, "Shelve": False, "Acknowledge": True, "Reset": True}, {"Warning": False, "Trip": True, "Unacked": False, "Shelved": False, "LockedOut": True}),
            step({"WarningCondition": False, "TripCondition": False, "Enable": False, "Shelve": False, "Acknowledge": False, "Reset": True}, {"Warning": False, "Trip": False, "Unacked": False, "Shelved": False, "LockedOut": False}),
        ], "Override shelving with a trip and require disabled clear conditions.")],
        internal_vars=["WarningDelay : TON;", "NewWarning : BOOL;"],
        iec_features=["FUNCTION_BLOCK", "BOOL", "TIME", "TON", "retained alarm", "shelving", "acknowledgement", "priority"],
        assumptions=["The runtime scan period is 100 ms.", "Acknowledge may be held for more than one scan.", "Each test starts from a fresh function-block instance."],
        complexity={"retained_state": 5, "transitions": 11, "stateful_blocks": 1, "interactions": 10, "fault_modes": 4, "horizon_scans": 12},
    ))

    items.append(task(
        "C10_X01_three_pump_feedback_dispatch",
        "Three-pump staged dispatch with lead preference and feedback exclusion",
        "C10", "hard",
        [
            var("LowDemand", "BOOL", "One-pump demand"), var("HighDemand", "BOOL", "Two-pump demand"),
            var("Lead", "INT", "Preferred pump 1, 2, or 3"), var("Available1", "BOOL", "Pump 1 availability"),
            var("Available2", "BOOL", "Pump 2 availability"), var("Available3", "BOOL", "Pump 3 availability"),
            var("Feedback1", "BOOL", "Pump 1 running feedback"), var("Feedback2", "BOOL", "Pump 2 running feedback"),
            var("Feedback3", "BOOL", "Pump 3 running feedback"), var("Stop", "BOOL", "Immediate stop"),
            var("Reset", "BOOL", "Failure reset"),
        ],
        [
            var("Run1", "BOOL", "Pump 1 command"), var("Run2", "BOOL", "Pump 2 command"),
            var("Run3", "BOOL", "Pump 3 command"), var("ActiveCount", "INT", "Number of commanded pumps"),
            var("Failover", "BOOL", "Lead or requested capacity was replaced"), var("Fault", "BOOL", "Latched insufficient-capacity fault"),
        ],
        [
            req("LowDemand shall request one pump and HighDemand shall request two, with HighDemand taking priority.", "G(required_count = mux(HighDemand,2,mux(LowDemand,1,0)))"),
            req("Dispatch shall prefer Lead, then the next pump numbers cyclically, excluding unavailable or feedback-failed pumps.", "G(dispatched_order = cyclic_available_order(Lead))"),
            req("A commanded pump without feedback for 300 ms shall be excluded and replaced when capacity permits.", "G(no_feedback_3 -> !corresponding_run)", True),
            req("ActiveCount shall equal the number of TRUE run outputs, and no more than two pumps may run.", "G(ActiveCount=count_true(Run1,Run2,Run3)) AND G(ActiveCount<=2)", True),
            req("Failover shall be TRUE when an unhealthy preferred pump is bypassed or requested capacity cannot be met; insufficient capacity shall latch Fault.", "G(ActiveCount<required_count -> (Failover AND Fault))", True),
            req("Stop shall immediately clear every run command; Reset clears failures only while both demand inputs and Stop are FALSE.", "G(Stop -> (!Run1 AND !Run2 AND !Run3)) AND G(qualified_reset -> !Fault)", True),
        ],
        """NoFeedback1(IN := Run1 AND (NOT Feedback1), PT := T#300ms);
NoFeedback2(IN := Run2 AND (NOT Feedback2), PT := T#300ms);
NoFeedback3(IN := Run3 AND (NOT Feedback3), PT := T#300ms);
IF NoFeedback1.Q THEN Failed1 := TRUE; END_IF;
IF NoFeedback2.Q THEN Failed2 := TRUE; END_IF;
IF NoFeedback3.Q THEN Failed3 := TRUE; END_IF;
IF Reset AND (NOT LowDemand) AND (NOT HighDemand) AND (NOT Stop) THEN
    Failed1 := FALSE; Failed2 := FALSE; Failed3 := FALSE; Fault := FALSE;
END_IF;
Run1 := FALSE; Run2 := FALSE; Run3 := FALSE;
RequiredCount := 0;
IF HighDemand THEN RequiredCount := 2;
ELSIF LowDemand THEN RequiredCount := 1;
END_IF;
Valid1 := Available1 AND (NOT Failed1);
Valid2 := Available2 AND (NOT Failed2);
Valid3 := Available3 AND (NOT Failed3);
IF (NOT Stop) AND (RequiredCount > 0) THEN
    IF Lead = 2 THEN
        IF Valid2 THEN Run2 := TRUE;
        ELSIF Valid3 THEN Run3 := TRUE;
        ELSIF Valid1 THEN Run1 := TRUE;
        END_IF;
        IF RequiredCount = 2 THEN
            IF Valid3 AND (NOT Run3) THEN Run3 := TRUE;
            ELSIF Valid1 AND (NOT Run1) THEN Run1 := TRUE;
            ELSIF Valid2 AND (NOT Run2) THEN Run2 := TRUE;
            END_IF;
        END_IF;
    ELSIF Lead = 3 THEN
        IF Valid3 THEN Run3 := TRUE;
        ELSIF Valid1 THEN Run1 := TRUE;
        ELSIF Valid2 THEN Run2 := TRUE;
        END_IF;
        IF RequiredCount = 2 THEN
            IF Valid1 AND (NOT Run1) THEN Run1 := TRUE;
            ELSIF Valid2 AND (NOT Run2) THEN Run2 := TRUE;
            ELSIF Valid3 AND (NOT Run3) THEN Run3 := TRUE;
            END_IF;
        END_IF;
    ELSE
        IF Valid1 THEN Run1 := TRUE;
        ELSIF Valid2 THEN Run2 := TRUE;
        ELSIF Valid3 THEN Run3 := TRUE;
        END_IF;
        IF RequiredCount = 2 THEN
            IF Valid2 AND (NOT Run2) THEN Run2 := TRUE;
            ELSIF Valid3 AND (NOT Run3) THEN Run3 := TRUE;
            ELSIF Valid1 AND (NOT Run1) THEN Run1 := TRUE;
            END_IF;
        END_IF;
    END_IF;
END_IF;
ActiveCount := 0;
IF Run1 THEN ActiveCount := ActiveCount + 1; END_IF;
IF Run2 THEN ActiveCount := ActiveCount + 1; END_IF;
IF Run3 THEN ActiveCount := ActiveCount + 1; END_IF;
Failover := (RequiredCount > 0) AND ((ActiveCount < RequiredCount) OR ((Lead = 1) AND (NOT Run1)) OR ((Lead = 2) AND (NOT Run2)) OR ((Lead = 3) AND (NOT Run3)));
IF ActiveCount < RequiredCount THEN Fault := TRUE; END_IF;""",
        [test("healthy_lead_and_staging", ["R1", "R2", "R4"], [
            step({"LowDemand": True, "HighDemand": False, "Lead": 2, "Available1": True, "Available2": True, "Available3": True, "Feedback1": False, "Feedback2": True, "Feedback3": False, "Stop": False, "Reset": False}, {"Run1": False, "Run2": True, "Run3": False, "ActiveCount": 1, "Failover": False, "Fault": False}),
            step({"LowDemand": True, "HighDemand": True, "Lead": 2, "Available1": True, "Available2": True, "Available3": True, "Feedback1": False, "Feedback2": True, "Feedback3": True, "Stop": False, "Reset": False}, {"Run1": False, "Run2": True, "Run3": True, "ActiveCount": 2, "Failover": False, "Fault": False}),
        ], "Run the healthy lead and add the cyclic follower.")],
        [test("feedback_exclusion_capacity_fault_reset", ["R3", "R4", "R5", "R6"], [
            step({"LowDemand": True, "HighDemand": True, "Lead": 1, "Available1": True, "Available2": True, "Available3": True, "Feedback1": False, "Feedback2": True, "Feedback3": True, "Stop": False, "Reset": False}, {"Run1": False, "Run2": True, "Run3": True, "ActiveCount": 2, "Failover": True, "Fault": False}, repeat=5, check="last_only"),
            step({"LowDemand": True, "HighDemand": True, "Lead": 1, "Available1": False, "Available2": True, "Available3": False, "Feedback1": False, "Feedback2": True, "Feedback3": False, "Stop": False, "Reset": False}, {"Run1": False, "Run2": True, "Run3": False, "ActiveCount": 1, "Failover": True, "Fault": True}),
            step({"LowDemand": False, "HighDemand": False, "Lead": 1, "Available1": True, "Available2": True, "Available3": True, "Feedback1": False, "Feedback2": False, "Feedback3": False, "Stop": False, "Reset": True}, {"Run1": False, "Run2": False, "Run3": False, "ActiveCount": 0, "Failover": False, "Fault": False}),
        ], "Exclude a failed lead, report capacity loss, and reset only idle.")],
        internal_vars=[
            "NoFeedback1 : TON;", "NoFeedback2 : TON;", "NoFeedback3 : TON;",
            "Failed1 : BOOL;", "Failed2 : BOOL;", "Failed3 : BOOL;",
            "Valid1 : BOOL;", "Valid2 : BOOL;", "Valid3 : BOOL;", "RequiredCount : INT;",
        ],
        iec_features=["FUNCTION_BLOCK", "BOOL", "INT", "TIME", "TON", "multi-device dispatch", "cyclic priority", "feedback exclusion"],
        assumptions=["The runtime scan period is 100 ms.", "At most two pumps are required simultaneously.", "Each test starts from a fresh function-block instance."],
        complexity={"retained_state": 5, "transitions": 14, "stateful_blocks": 3, "interactions": 12, "fault_modes": 5, "horizon_scans": 14},
    ))

    return items
