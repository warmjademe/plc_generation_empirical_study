FUNCTION_BLOCK C08_B15_composite
VAR_INPUT
    A_Start : BOOL;
    A_HighLevel : BOOL;
    A_MixDone : BOOL;
    A_LowLevel : BOOL;
    A_Abort : BOOL;
    B_ItemPresent : BOOL;
    B_RejectClass : BOOL;
    B_TransferDone : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_FillValve : BOOL;
    A_Mixer : BOOL;
    A_DrainValve : BOOL;
    A_Complete : BOOL;
    A_State : INT;
    B_Inspect : BOOL;
    B_AcceptGate : BOOL;
    B_RejectGate : BOOL;
    B_State : INT;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
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
