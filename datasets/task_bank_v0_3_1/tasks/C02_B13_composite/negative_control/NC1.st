FUNCTION_BLOCK C02_B13_composite
VAR_INPUT
    A_RemoteMode : BOOL;
    A_LocalStart : BOOL;
    A_RemoteStart : BOOL;
    A_Stop : BOOL;
    A_Permit : BOOL;
    B_Start : BOOL;
    B_Stop : BOOL;
    B_Fault : BOOL;
    B_Reset : BOOL;
    B_Permit : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Running : BOOL;
    A_SelectedStart : BOOL;
    B_Running : BOOL;
    B_LockedOut : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR

A_SelectedStart := (A_RemoteMode AND A_RemoteStart) OR ((NOT A_RemoteMode) AND A_LocalStart);
IF A_Stop OR (NOT A_Permit) THEN
    A_Running := FALSE;
ELSIF A_SelectedStart THEN
    A_Running := TRUE;
END_IF;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Running THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := FALSE;

IF SubsystemBEnable AND CrossReady THEN
    IF B_Fault THEN
        B_LockedOut := TRUE;
        B_Running := FALSE;
    ELSIF B_Reset AND (NOT B_Start) THEN
        B_LockedOut := FALSE;
    END_IF;

    IF B_LockedOut OR B_Stop OR (NOT B_Permit) THEN
        B_Running := FALSE;
    ELSIF B_Start THEN
        B_Running := TRUE;
    END_IF;
ELSE
    B_Running := FALSE;
    B_LockedOut := FALSE;
END_IF;

END_FUNCTION_BLOCK
