FUNCTION_BLOCK C08_B17_composite
VAR_INPUT
    A_Start : BOOL;
    A_Stage1Done : BOOL;
    A_Stage2Done : BOOL;
    A_Stage3Done : BOOL;
    A_Pause : BOOL;
    A_Abort : BOOL;
    A_Reset : BOOL;
    B_Start : BOOL;
    B_Advance : BOOL;
    B_Pause : BOOL;
    B_Resume : BOOL;
    B_Abort : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Actuator1 : BOOL;
    A_Actuator2 : BOOL;
    A_Actuator3 : BOOL;
    A_Paused : BOOL;
    A_Complete : BOOL;
    A_Fault : BOOL;
    A_State : INT;
    B_Step1 : BOOL;
    B_Step2 : BOOL;
    B_Paused : BOOL;
    B_Aborted : BOOL;
    B_State : INT;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_StageTimer : TON;
END_VAR

A_Complete := FALSE;
A_StageTimer(IN := (A_State > 0) AND (NOT A_Pause), PT := T#500ms);
IF A_Abort THEN
    A_State := 0;
    A_Fault := FALSE;
ELSIF A_StageTimer.Q THEN
    A_State := 0;
    A_Fault := TRUE;
ELSIF (A_State = 0) AND A_Reset AND (NOT A_Start) AND (NOT A_Abort) AND (NOT A_Stage1Done) AND (NOT A_Stage2Done) AND (NOT A_Stage3Done) THEN
    A_Fault := FALSE;
ELSIF NOT A_Fault THEN
    IF (A_State = 0) AND A_Start THEN
        A_State := 1;
    ELSIF NOT A_Pause THEN
        CASE A_State OF
            1: IF A_Stage1Done THEN A_State := 2; END_IF;
            2: IF A_Stage2Done THEN A_State := 3; END_IF;
            3: IF A_Stage3Done THEN A_State := 0; A_Complete := TRUE; END_IF;
            ELSE A_State := 0;
        END_CASE;
    END_IF;
END_IF;
A_Paused := (A_State > 0) AND A_Pause AND (NOT A_Fault);
A_Actuator1 := (A_State = 1) AND (NOT A_Pause) AND (NOT A_Fault);
A_Actuator2 := (A_State = 2) AND (NOT A_Pause) AND (NOT A_Fault);
A_Actuator3 := (A_State = 3) AND (NOT A_Pause) AND (NOT A_Fault);

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Actuator1 THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

IF SubsystemBEnable AND CrossReady THEN
    IF B_Abort THEN
        B_State := 0;
        B_Paused := FALSE;
        B_Aborted := TRUE;
    ELSIF B_Reset AND (NOT B_Start) AND (NOT B_Advance) AND (NOT B_Pause) AND (NOT B_Resume) THEN
        B_Aborted := FALSE;
    ELSIF NOT B_Aborted THEN
        IF B_Pause AND ((B_State = 1) OR (B_State = 2)) THEN
            B_Paused := TRUE;
        ELSIF B_Resume THEN
            B_Paused := FALSE;
        END_IF;
        IF NOT B_Paused THEN
            CASE B_State OF
                0: IF B_Start THEN B_State := 1; END_IF;
                1: IF B_Advance THEN B_State := 2; END_IF;
                2: IF B_Advance THEN B_State := 3; END_IF;
                3: B_State := 3;
                ELSE B_State := 0;
            END_CASE;
        END_IF;
    END_IF;
    B_Step1 := (B_State = 1) AND (NOT B_Paused) AND (NOT B_Aborted);
    B_Step2 := (B_State = 2) AND (NOT B_Paused) AND (NOT B_Aborted);
ELSE
    B_Step1 := FALSE;
    B_Step2 := FALSE;
    B_Paused := FALSE;
    B_Aborted := FALSE;
    B_State := 0;
END_IF;

END_FUNCTION_BLOCK
