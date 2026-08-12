FUNCTION_BLOCK C02_B12_composite
VAR_INPUT
    A_Enable : BOOL;
    A_Start : BOOL;
    A_Stop : BOOL;
    B_AutoMode : BOOL;
    B_AutoStart : BOOL;
    B_ManualStart : BOOL;
    B_Stop : BOOL;
    B_Enable : BOOL;
    B_SafetyOK : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Running : BOOL;
    A_Ready : BOOL;
    B_Running : BOOL;
    B_RestartRequired : BOOL;
    B_RejectedStart : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    B_SelectedStart : BOOL;
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
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

IF SubsystemBEnable AND CrossReady THEN
    B_SelectedStart := (B_AutoMode AND B_AutoStart) OR ((NOT B_AutoMode) AND B_ManualStart);
    B_RejectedStart := FALSE;
    IF B_Stop OR (NOT B_Enable) THEN
        B_Running := FALSE;
    ELSIF NOT B_SafetyOK THEN
        IF B_Running OR B_SelectedStart THEN B_RestartRequired := TRUE; END_IF;
        B_Running := FALSE;
    ELSIF B_RestartRequired THEN
        B_Running := FALSE;
        IF B_SelectedStart THEN B_RejectedStart := TRUE; END_IF;
        IF B_Reset AND B_Enable AND B_SafetyOK AND (NOT B_SelectedStart) THEN B_RestartRequired := FALSE; END_IF;
    ELSIF B_SelectedStart THEN
        B_Running := TRUE;
    END_IF;
ELSE
    B_Running := FALSE;
    B_RestartRequired := FALSE;
    B_RejectedStart := FALSE;
END_IF;

END_FUNCTION_BLOCK
