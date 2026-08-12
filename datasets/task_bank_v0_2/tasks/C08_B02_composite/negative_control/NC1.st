FUNCTION_BLOCK C08_B02_composite
VAR_INPUT
    A_Start : BOOL;
    A_Advance : BOOL;
    A_Pause : BOOL;
    A_Resume : BOOL;
    A_Abort : BOOL;
    A_Reset : BOOL;
    B_ItemPresent : BOOL;
    B_RejectClass : BOOL;
    B_TransferDone : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Step1 : BOOL;
    A_Step2 : BOOL;
    A_Paused : BOOL;
    A_Aborted : BOOL;
    A_State : INT;
    B_Inspect : BOOL;
    B_AcceptGate : BOOL;
    B_RejectGate : BOOL;
    B_State : INT;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR

IF A_Abort THEN
    A_State := 0;
    A_Paused := FALSE;
    A_Aborted := FALSE;
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
