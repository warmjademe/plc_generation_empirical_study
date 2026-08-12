FUNCTION_BLOCK C02_B07_composite
VAR_INPUT
    A_PowerOK : BOOL;
    A_SafetyOK : BOOL;
    A_Start : BOOL;
    A_Stop : BOOL;
    A_Reset : BOOL;
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
    A_RestartInhibit : BOOL;
    B_Running : BOOL;
    B_SelectedStart : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR

IF (NOT A_PowerOK) OR (NOT A_SafetyOK) THEN
    A_Running := FALSE;
    A_RestartInhibit := TRUE;
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
CrossBlocked := FALSE;

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
