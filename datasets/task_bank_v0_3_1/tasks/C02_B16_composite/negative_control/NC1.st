FUNCTION_BLOCK C02_B16_composite
VAR_INPUT
    A_RemoteMode : BOOL;
    A_LocalStart : BOOL;
    A_RemoteStart : BOOL;
    A_Stop : BOOL;
    A_Permit : BOOL;
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
    A_SelectedStart : BOOL;
    B_Running : BOOL;
    B_RestartRequired : BOOL;
    B_RejectedStart : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    B_SelectedStart : BOOL;
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
