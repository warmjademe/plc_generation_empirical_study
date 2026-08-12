FUNCTION_BLOCK C06_U07_lean_composite
VAR_INPUT
    A_Inspected : BOOL;
    A_Rejected : BOOL;
    A_Reset : BOOL;
    A_WindowSize : INT;
    A_RejectLimit : INT;
    B_ChA : BOOL;
    B_ChB : BOOL;
    B_TestMode : BOOL;
    B_TestPermit : BOOL;
    B_ProcessRequest : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_WindowCount : INT;
    A_RejectCount : INT;
    A_LockedOut : BOOL;
    A_WindowComplete : BOOL;
    B_SafeEnable : BOOL;
    B_Disagree : BOOL;
    B_TestActive : BOOL;
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
    B_Disagree := B_ChA <> B_ChB;
    B_TestActive := B_TestMode AND B_TestPermit;
    IF B_TestMode THEN
        B_SafeEnable := B_ProcessRequest AND B_TestPermit AND B_ChA;
    ELSE
        B_SafeEnable := B_ProcessRequest AND B_ChA AND B_ChB;
    END_IF;
ELSE
    B_SafeEnable := FALSE;
    B_Disagree := FALSE;
    B_TestActive := FALSE;
END_IF;

END_FUNCTION_BLOCK
