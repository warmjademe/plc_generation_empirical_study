FUNCTION_BLOCK C08_B08_composite
VAR_INPUT
    A_Start : BOOL;
    A_Sensor1 : BOOL;
    A_Sensor2 : BOOL;
    A_Stop : BOOL;
    A_ResetFault : BOOL;
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
    A_Actuator1 : BOOL;
    A_Actuator2 : BOOL;
    A_Complete : BOOL;
    A_Fault : BOOL;
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
    A_StageTimeout : TON;
    B_StageTimer : TON;
END_VAR

A_Complete := FALSE;
A_StageTimeout(IN := (A_State = 1) OR (A_State = 2), PT := T#500ms);
IF A_StageTimeout.Q THEN
    A_Fault := FALSE;
    A_State := 0;
ELSIF A_Stop THEN
    A_State := 0;
    IF A_ResetFault AND (NOT A_Start) THEN
        A_Fault := FALSE;
    END_IF;
ELSIF NOT A_Fault THEN
    CASE A_State OF
        0: IF A_Start THEN A_State := 1; END_IF;
        1: IF A_Sensor1 THEN A_State := 2; END_IF;
        2: IF A_Sensor2 THEN A_State := 0; A_Complete := TRUE; END_IF;
        ELSE A_State := 0;
    END_CASE;
END_IF;
A_Actuator1 := (A_State = 1) AND (NOT A_Fault);
A_Actuator2 := (A_State = 2) AND (NOT A_Fault);

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Actuator1 THEN
    CrossReady := TRUE;
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
