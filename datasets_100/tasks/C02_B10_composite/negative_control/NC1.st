FUNCTION_BLOCK C02_B10_composite
VAR_INPUT
    A_Enable : BOOL;
    A_Start : BOOL;
    A_Stop : BOOL;
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
    A_Ready : BOOL;
    B_Running : BOOL;
    B_RestartInhibit : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR

A_Ready := A_Enable AND (NOT A_Stop);
IF (NOT A_Enable) OR A_Stop THEN
    A_Running := FALSE;
ELSIF A_Start AND A_Ready THEN
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
