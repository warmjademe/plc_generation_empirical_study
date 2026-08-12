FUNCTION_BLOCK C08_B10_composite
VAR_INPUT
    A_ItemPresent : BOOL;
    A_RejectClass : BOOL;
    A_TransferDone : BOOL;
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
    A_Inspect : BOOL;
    A_AcceptGate : BOOL;
    A_RejectGate : BOOL;
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
    CrossReady := TRUE;
END_IF;
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

IF SubsystemBEnable AND CrossReady THEN
    B_Complete := FALSE;
    B_StageTimeout(IN := (B_State = 1) OR (B_State = 2), PT := T#500ms);
    IF B_Stop THEN
        B_State := 0;
        IF B_ResetFault AND (NOT B_Start) THEN
            B_Fault := FALSE;
        END_IF;
    ELSIF B_StageTimeout.Q THEN
        B_Fault := TRUE;
        B_State := 0;
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
