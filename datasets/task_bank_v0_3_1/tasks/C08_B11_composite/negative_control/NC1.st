FUNCTION_BLOCK C08_B11_composite
VAR_INPUT
    A_ItemPresent : BOOL;
    A_RejectClass : BOOL;
    A_TransferDone : BOOL;
    A_Reset : BOOL;
    B_Start : BOOL;
    B_HighLevel : BOOL;
    B_MixDone : BOOL;
    B_LowLevel : BOOL;
    B_Abort : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Inspect : BOOL;
    A_AcceptGate : BOOL;
    A_RejectGate : BOOL;
    A_State : INT;
    B_FillValve : BOOL;
    B_Mixer : BOOL;
    B_DrainValve : BOOL;
    B_Complete : BOOL;
    B_State : INT;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
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
CrossBlocked := FALSE;

IF SubsystemBEnable AND CrossReady THEN
    B_Complete := FALSE;
    IF B_Abort THEN
        B_State := 0;
    ELSE
        CASE B_State OF
            0: IF B_Start THEN B_State := 1; END_IF;
            1: IF B_HighLevel THEN B_State := 2; END_IF;
            2: IF B_MixDone THEN B_State := 3; END_IF;
            3: IF B_LowLevel THEN B_State := 0; B_Complete := TRUE; END_IF;
            ELSE B_State := 0;
        END_CASE;
    END_IF;
    B_FillValve := B_State = 1;
    B_Mixer := B_State = 2;
    B_DrainValve := B_State = 3;
ELSE
    B_FillValve := FALSE;
    B_Mixer := FALSE;
    B_DrainValve := FALSE;
    B_Complete := FALSE;
    B_State := 0;
END_IF;

END_FUNCTION_BLOCK
