FUNCTION_BLOCK C08_B06_composite
VAR_INPUT
    A_Start : BOOL;
    A_Sensor1 : BOOL;
    A_Sensor2 : BOOL;
    A_Stop : BOOL;
    A_ResetFault : BOOL;
    B_ItemPresent : BOOL;
    B_RejectClass : BOOL;
    B_TransferDone : BOOL;
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
    B_Inspect : BOOL;
    B_AcceptGate : BOOL;
    B_RejectGate : BOOL;
    B_State : INT;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_StageTimeout : TON;
END_VAR

A_Complete := FALSE;
A_StageTimeout(IN := (A_State = 1) OR (A_State = 2), PT := T#500ms);
IF A_Stop THEN
    A_State := 0;
    IF A_ResetFault AND (NOT A_Start) THEN
        A_Fault := FALSE;
    END_IF;
ELSIF A_StageTimeout.Q THEN
    A_Fault := TRUE;
    A_State := 0;
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
    IF B_Reset THEN
        B_State := 0;
    ELSE
        CASE B_State OF
            0: IF B_ItemPresent THEN B_State := 1; END_IF;
            1: IF B_RejectClass THEN B_State := 3; ELSE B_State := 2; END_IF;
            2: IF B_TransferDone THEN B_State := 0; END_IF;
            3: IF B_TransferDone THEN B_State := 0; END_IF;
            ELSE B_State := 0;
        END_CASE;
    END_IF;
    B_Inspect := B_State = 1;
    B_AcceptGate := B_State = 2;
    B_RejectGate := B_State = 3;
ELSE
    B_Inspect := FALSE;
    B_AcceptGate := FALSE;
    B_RejectGate := FALSE;
    B_State := 0;
END_IF;

END_FUNCTION_BLOCK
