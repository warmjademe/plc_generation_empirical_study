FUNCTION_BLOCK C06_R06_lean_composite
VAR_INPUT
    A_Inspected : BOOL;
    A_Rejected : BOOL;
    A_Reset : BOOL;
    A_WindowSize : INT;
    A_RejectLimit : INT;
    B_Info : BOOL;
    B_Warning : BOOL;
    B_Trip : BOOL;
    B_Emergency : BOOL;
    B_Suppress : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_WindowCount : INT;
    A_RejectCount : INT;
    A_LockedOut : BOOL;
    A_WindowComplete : BOOL;
    B_Active : BOOL;
    B_Level : INT;
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
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

IF SubsystemBEnable AND CrossReady THEN
    IF B_Emergency THEN
        B_Level := 4;
        B_Active := TRUE;
    ELSIF B_Suppress THEN
        B_Level := 0;
        B_Active := FALSE;
    ELSIF B_Trip THEN
        B_Level := 3;
        B_Active := TRUE;
    ELSIF B_Warning THEN
        B_Level := 2;
        B_Active := TRUE;
    ELSIF B_Info THEN
        B_Level := 1;
        B_Active := TRUE;
    ELSE
        B_Level := 0;
        B_Active := FALSE;
    END_IF;
ELSE
    B_Active := FALSE;
    B_Level := 0;
END_IF;

END_FUNCTION_BLOCK
