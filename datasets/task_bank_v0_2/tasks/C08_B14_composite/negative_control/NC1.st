FUNCTION_BLOCK C08_B14_composite
VAR_INPUT
    A_Start : BOOL;
    A_HighLevel : BOOL;
    A_MixDone : BOOL;
    A_LowLevel : BOOL;
    A_Abort : BOOL;
    B_Start : BOOL;
    B_Sensor1 : BOOL;
    B_Sensor2 : BOOL;
    B_Stop : BOOL;
    B_ResetFault : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_FillValve : BOOL;
    A_Mixer : BOOL;
    A_DrainValve : BOOL;
    A_Complete : BOOL;
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

A_Complete := FALSE;
IF A_Abort THEN
    A_State := 0;
ELSE
    CASE A_State OF
        0: IF A_Start THEN A_State := 1; END_IF;
        1: IF A_HighLevel THEN A_State := 2; END_IF;
        2: IF A_MixDone THEN A_State := 3; END_IF;
        3: IF A_LowLevel THEN A_State := 0; A_Complete := FALSE; END_IF;
        ELSE A_State := 0;
    END_CASE;
END_IF;
A_FillValve := A_State = 1;
A_Mixer := A_State = 2;
A_DrainValve := A_State = 3;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_FillValve THEN
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
