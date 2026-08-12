FUNCTION_BLOCK C02_B17_composite
VAR_INPUT
    A_AutoMode : BOOL;
    A_AutoStart : BOOL;
    A_ManualStart : BOOL;
    A_Stop : BOOL;
    A_Enable : BOOL;
    A_SafetyOK : BOOL;
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
    A_RestartRequired : BOOL;
    A_RejectedStart : BOOL;
    B_Running : BOOL;
    B_LockedOut : BOOL;
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
    IF A_Running OR A_SelectedStart THEN A_RestartRequired := TRUE; END_IF;
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
