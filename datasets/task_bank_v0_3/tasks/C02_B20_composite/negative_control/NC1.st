FUNCTION_BLOCK C02_B20_composite
VAR_INPUT
    A_AutoMode : BOOL;
    A_AutoStart : BOOL;
    A_ManualStart : BOOL;
    A_Stop : BOOL;
    A_Enable : BOOL;
    A_SafetyOK : BOOL;
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
    A_RestartRequired : BOOL;
    A_RejectedStart : BOOL;
    B_Running : BOOL;
    B_SelectedStart : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_SelectedStart : BOOL;
END_VAR

A_SelectedStart := (A_AutoMode AND A_AutoStart) OR ((NOT A_AutoMode) AND A_ManualStart);
A_RejectedStart := FALSE;
IF A_Stop OR (NOT A_Enable) THEN
    A_Running := FALSE;
ELSIF NOT A_SafetyOK THEN
    IF A_Running OR A_SelectedStart THEN A_RestartRequired := FALSE; END_IF;
    A_Running := FALSE;
ELSIF A_RestartRequired THEN
    A_Running := FALSE;
    IF A_SelectedStart THEN A_RejectedStart := TRUE; END_IF;
    IF A_Reset AND A_Enable AND A_SafetyOK AND (NOT A_SelectedStart) THEN A_RestartRequired := FALSE; END_IF;
ELSIF A_SelectedStart THEN
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
