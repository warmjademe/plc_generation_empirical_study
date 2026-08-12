FUNCTION_BLOCK C08_B01_composite
VAR_INPUT
    A_Start : BOOL;
    A_Advance : BOOL;
    A_Pause : BOOL;
    A_Resume : BOOL;
    A_Abort : BOOL;
    A_Reset : BOOL;
    B_Start : BOOL;
    B_Sensor1 : BOOL;
    B_Sensor2 : BOOL;
    B_Stop : BOOL;
    B_ResetFault : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Step1 : BOOL;
    A_Step2 : BOOL;
    A_Paused : BOOL;
    A_Aborted : BOOL;
    A_State : INT;
    B_Actuator1 : BOOL;
    B_Actuator2 : BOOL;
    B_Complete : BOOL;
    B_Fault : BOOL;
    B_State : INT;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    B_StageTimeout : TON;
END_VAR

IF A_Abort THEN
    A_State := 0;
    A_Paused := FALSE;
    A_Aborted := TRUE;
ELSIF A_Reset AND (NOT A_Start) AND (NOT A_Advance) AND (NOT A_Pause) AND (NOT A_Resume) THEN
    A_Aborted := FALSE;
ELSIF NOT A_Aborted THEN
    IF A_Pause AND ((A_State = 1) OR (A_State = 2)) THEN
        A_Paused := TRUE;
    ELSIF A_Resume THEN
        A_Paused := FALSE;
    END_IF;
    IF NOT A_Paused THEN
        CASE A_State OF
            0: IF A_Start THEN A_State := 1; END_IF;
            1: IF A_Advance THEN A_State := 2; END_IF;
            2: IF A_Advance THEN A_State := 3; END_IF;
            3: A_State := 3;
            ELSE A_State := 0;
        END_CASE;
    END_IF;
END_IF;
A_Step1 := (A_State = 1) AND (NOT A_Paused) AND (NOT A_Aborted);
A_Step2 := (A_State = 2) AND (NOT A_Paused) AND (NOT A_Aborted);

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Step1 THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

IF SubsystemBEnable AND CrossReady THEN
    B_Complete := FALSE;
    B_StageTimeout(IN := (B_State = 1) OR (B_State = 2), PT := T#500ms);
    IF B_StageTimeout.Q THEN
        B_Fault := TRUE;
        B_State := 0;
    ELSIF B_Stop THEN
        B_State := 0;
        IF B_ResetFault AND (NOT B_Start) THEN
            B_Fault := FALSE;
        END_IF;
    ELSIF NOT B_Fault THEN
        CASE B_State OF
            0: IF B_Start THEN B_State := 1; END_IF;
            1: IF B_Sensor1 THEN B_State := 2; END_IF;
            2: IF B_Sensor2 THEN B_State := 0; B_Complete := TRUE; END_IF;
            ELSE B_State := 0;
        END_CASE;
    END_IF;
    B_Actuator1 := (B_State = 1) AND (NOT B_Fault);
    B_Actuator2 := (B_State = 2) AND (NOT B_Fault);
ELSE
    B_Actuator1 := FALSE;
    B_Actuator2 := FALSE;
    B_Complete := FALSE;
    B_Fault := FALSE;
    B_State := 0;
END_IF;

END_FUNCTION_BLOCK
