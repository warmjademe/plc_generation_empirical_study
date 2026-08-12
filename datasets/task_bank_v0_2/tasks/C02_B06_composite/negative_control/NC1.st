FUNCTION_BLOCK C02_B06_composite
VAR_INPUT
    A_PowerOK : BOOL;
    A_SafetyOK : BOOL;
    A_Start : BOOL;
    A_Stop : BOOL;
    A_Reset : BOOL;
    B_Enable : BOOL;
    B_Start : BOOL;
    B_Stop : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Running : BOOL;
    A_RestartInhibit : BOOL;
    B_Running : BOOL;
    B_Ready : BOOL;
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
    B_Ready := B_Enable AND (NOT B_Stop);
    IF (NOT B_Enable) OR B_Stop THEN
        B_Running := FALSE;
    ELSIF B_Start AND B_Ready THEN
        B_Running := TRUE;
    END_IF;
ELSE
    B_Running := FALSE;
    B_Ready := FALSE;
END_IF;

END_FUNCTION_BLOCK
