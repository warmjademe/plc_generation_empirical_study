FUNCTION_BLOCK C02_B03_composite
VAR_INPUT
    A_Start : BOOL;
    A_Stop : BOOL;
    A_Fault : BOOL;
    A_Reset : BOOL;
    A_Permit : BOOL;
    B_RemoteMode : BOOL;
    B_LocalStart : BOOL;
    B_RemoteStart : BOOL;
    B_Stop : BOOL;
    B_Permit : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Running : BOOL;
    A_LockedOut : BOOL;
    B_Running : BOOL;
    B_SelectedStart : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR

IF A_Fault THEN
    A_LockedOut := TRUE;
    A_Running := FALSE;
ELSIF A_Reset AND (NOT A_Start) THEN
    A_LockedOut := FALSE;
END_IF;

IF A_LockedOut OR A_Stop OR (NOT A_Permit) THEN
    A_Running := FALSE;
ELSIF A_Start THEN
    A_Running := TRUE;
END_IF;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Running THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

IF SubsystemBEnable AND CrossReady THEN
    B_SelectedStart := (B_RemoteMode AND B_RemoteStart) OR ((NOT B_RemoteMode) AND B_LocalStart);
    IF B_Stop OR (NOT B_Permit) THEN
        B_Running := FALSE;
    ELSIF B_SelectedStart THEN
        B_Running := TRUE;
    END_IF;
ELSE
    B_Running := FALSE;
    B_SelectedStart := FALSE;
END_IF;

END_FUNCTION_BLOCK
