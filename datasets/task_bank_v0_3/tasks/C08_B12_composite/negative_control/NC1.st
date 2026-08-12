FUNCTION_BLOCK C08_B12_composite
VAR_INPUT
    A_ItemPresent : BOOL;
    A_RejectClass : BOOL;
    A_TransferDone : BOOL;
    A_Reset : BOOL;
    B_Start : BOOL;
    B_Stage1Done : BOOL;
    B_Stage2Done : BOOL;
    B_Stage3Done : BOOL;
    B_Pause : BOOL;
    B_Abort : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Inspect : BOOL;
    A_AcceptGate : BOOL;
    A_RejectGate : BOOL;
    A_State : INT;
    B_Actuator1 : BOOL;
    B_Actuator2 : BOOL;
    B_Actuator3 : BOOL;
    B_Paused : BOOL;
    B_Complete : BOOL;
    B_Fault : BOOL;
    B_State : INT;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    B_StageTimer : TON;
END_VAR

IF A_Reset THEN
    A_State := 0;
ELSE
    CASE A_State OF
        0: IF A_ItemPresent THEN A_State := 1; END_IF;
        1: IF A_RejectClass THEN A_State := 3; ELSE A_State := 2; END_IF;
        2: IF A_TransferDone THEN A_State := 0; END_IF;
        3: IF A_TransferDone THEN A_State := 0; END_IF;
        ELSE A_State := 0;
    END_CASE;
END_IF;
A_Inspect := A_State = 1;
A_AcceptGate := A_State = 2;
A_RejectGate := A_State = 3;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Inspect THEN
    CrossReady := FALSE;
END_IF;
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

IF SubsystemBEnable AND CrossReady THEN
    B_Complete := FALSE;
    B_StageTimer(IN := (B_State > 0) AND (NOT B_Pause), PT := T#500ms);
    IF B_Abort THEN
        B_State := 0;
        B_Fault := TRUE;
    ELSIF B_StageTimer.Q THEN
        B_State := 0;
        B_Fault := TRUE;
    ELSIF (B_State = 0) AND B_Reset AND (NOT B_Start) AND (NOT B_Abort) AND (NOT B_Stage1Done) AND (NOT B_Stage2Done) AND (NOT B_Stage3Done) THEN
        B_Fault := FALSE;
    ELSIF NOT B_Fault THEN
        IF (B_State = 0) AND B_Start THEN
            B_State := 1;
        ELSIF NOT B_Pause THEN
            CASE B_State OF
                1: IF B_Stage1Done THEN B_State := 2; END_IF;
                2: IF B_Stage2Done THEN B_State := 3; END_IF;
                3: IF B_Stage3Done THEN B_State := 0; B_Complete := TRUE; END_IF;
                ELSE B_State := 0;
            END_CASE;
        END_IF;
    END_IF;
    B_Paused := (B_State > 0) AND B_Pause AND (NOT B_Fault);
    B_Actuator1 := (B_State = 1) AND (NOT B_Pause) AND (NOT B_Fault);
    B_Actuator2 := (B_State = 2) AND (NOT B_Pause) AND (NOT B_Fault);
    B_Actuator3 := (B_State = 3) AND (NOT B_Pause) AND (NOT B_Fault);
ELSE
    B_Actuator1 := FALSE;
    B_Actuator2 := FALSE;
    B_Actuator3 := FALSE;
    B_Paused := FALSE;
    B_Complete := FALSE;
    B_Fault := FALSE;
    B_State := 0;
END_IF;

END_FUNCTION_BLOCK
