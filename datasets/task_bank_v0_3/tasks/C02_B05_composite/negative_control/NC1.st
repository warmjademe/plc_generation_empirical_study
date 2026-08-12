FUNCTION_BLOCK C02_B05_composite
VAR_INPUT
    A_PowerOK : BOOL;
    A_SafetyOK : BOOL;
    A_Start : BOOL;
    A_Stop : BOOL;
    A_Reset : BOOL;
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
    A_RestartInhibit : BOOL;
    B_Running : BOOL;
    B_LockedOut : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR

IF (NOT A_PowerOK) OR (NOT A_SafetyOK) THEN
    A_Running := FALSE;
    A_RestartInhibit := FALSE;
ELSIF A_Stop THEN
    A_Running := FALSE;
ELSIF A_Reset AND (NOT A_Start) THEN
    A_RestartInhibit := FALSE;
ELSIF A_Start AND (NOT A_RestartInhibit) THEN
    A_Running := TRUE;
END_IF;

IF A_RestartInhibit THEN
    A_Running := FALSE;
END_IF;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Running THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

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
