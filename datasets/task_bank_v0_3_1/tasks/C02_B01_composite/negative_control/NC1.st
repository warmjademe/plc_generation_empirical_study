FUNCTION_BLOCK C02_B01_composite
VAR_INPUT
    A_Start : BOOL;
    A_Stop : BOOL;
    A_Fault : BOOL;
    A_Reset : BOOL;
    A_Permit : BOOL;
    B_PowerOK : BOOL;
    B_SafetyOK : BOOL;
    B_Start : BOOL;
    B_Stop : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Running : BOOL;
    A_LockedOut : BOOL;
    B_Running : BOOL;
    B_RestartInhibit : BOOL;
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
CrossBlocked := FALSE;

IF SubsystemBEnable AND CrossReady THEN
    IF (NOT B_PowerOK) OR (NOT B_SafetyOK) THEN
        B_Running := FALSE;
        B_RestartInhibit := TRUE;
    ELSIF B_Stop THEN
        B_Running := FALSE;
    ELSIF B_Reset AND (NOT B_Start) THEN
        B_RestartInhibit := FALSE;
    ELSIF B_Start AND (NOT B_RestartInhibit) THEN
        B_Running := TRUE;
    END_IF;

    IF B_RestartInhibit THEN
        B_Running := FALSE;
    END_IF;
ELSE
    B_Running := FALSE;
    B_RestartInhibit := FALSE;
END_IF;

END_FUNCTION_BLOCK
