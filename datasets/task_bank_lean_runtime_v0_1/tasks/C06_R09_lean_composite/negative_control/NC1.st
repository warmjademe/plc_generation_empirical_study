FUNCTION_BLOCK C06_R09_lean_composite
VAR_INPUT
    A_Inspected : BOOL;
    A_Rejected : BOOL;
    A_Reset : BOOL;
    A_WindowSize : INT;
    A_RejectLimit : INT;
    B_AutoMode : BOOL;
    B_AutoDemand : BOOL;
    B_ManualDemand : BOOL;
    B_SafetyOK : BOOL;
    B_Inhibit : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_WindowCount : INT;
    A_RejectCount : INT;
    A_LockedOut : BOOL;
    A_WindowComplete : BOOL;
    B_Command : BOOL;
    B_Blocked : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PrevInspected : BOOL := FALSE;
END_VAR

A_WindowComplete := FALSE;
IF A_Reset THEN
    A_WindowCount := 0;
    A_RejectCount := 0;
    A_LockedOut := FALSE;
ELSIF (NOT A_LockedOut) AND A_Inspected AND (NOT A_PrevInspected) THEN
    A_WindowCount := A_WindowCount + 1;
    IF A_Rejected THEN
        A_RejectCount := A_RejectCount + 1;
    END_IF;
    IF A_WindowCount >= A_WindowSize THEN
        IF A_RejectCount > A_RejectLimit THEN
            A_LockedOut := TRUE;
        END_IF;
        A_WindowCount := 0;
        A_RejectCount := 0;
        A_WindowComplete := TRUE;
    END_IF;
END_IF;
A_PrevInspected := A_Inspected;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_LockedOut THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := FALSE;

IF SubsystemBEnable AND CrossReady THEN
    B_Command := ((B_AutoMode AND B_AutoDemand) OR ((NOT B_AutoMode) AND B_ManualDemand))
               AND B_SafetyOK AND (NOT B_Inhibit);
    B_Blocked := ((B_AutoMode AND B_AutoDemand) OR ((NOT B_AutoMode) AND B_ManualDemand))
               AND ((NOT B_SafetyOK) OR B_Inhibit);
ELSE
    B_Command := FALSE;
    B_Blocked := FALSE;
END_IF;

END_FUNCTION_BLOCK
