FUNCTION_BLOCK C06_V07_lean_composite
VAR_INPUT
    A_ChA : BOOL;
    A_ChB : BOOL;
    A_TestMode : BOOL;
    A_TestPermit : BOOL;
    A_ProcessRequest : BOOL;
    B_Inspected : BOOL;
    B_Rejected : BOOL;
    B_Reset : BOOL;
    B_WindowSize : INT;
    B_RejectLimit : INT;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_SafeEnable : BOOL;
    A_Disagree : BOOL;
    A_TestActive : BOOL;
    B_WindowCount : INT;
    B_RejectCount : INT;
    B_LockedOut : BOOL;
    B_WindowComplete : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    B_PrevInspected : BOOL := FALSE;
END_VAR

A_Disagree := A_ChA <> A_ChB;
A_TestActive := A_TestMode AND A_TestPermit;
IF A_TestMode THEN
    A_SafeEnable := A_ProcessRequest AND A_TestPermit AND A_ChA;
ELSE
    A_SafeEnable := A_ProcessRequest AND A_ChA AND A_ChB;
END_IF;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_SafeEnable THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

IF SubsystemBEnable AND CrossReady THEN
    B_WindowComplete := FALSE;
    IF B_Reset THEN
        B_WindowCount := 0;
        B_RejectCount := 0;
        B_LockedOut := FALSE;
    ELSIF (NOT B_LockedOut) AND B_Inspected AND (NOT B_PrevInspected) THEN
        B_WindowCount := B_WindowCount + 1;
        IF B_Rejected THEN
            B_RejectCount := B_RejectCount + 1;
        END_IF;
        IF B_WindowCount >= B_WindowSize THEN
            IF B_RejectCount > B_RejectLimit THEN
                B_LockedOut := TRUE;
            END_IF;
            B_WindowCount := 0;
            B_RejectCount := 0;
            B_WindowComplete := TRUE;
        END_IF;
    END_IF;
    B_PrevInspected := B_Inspected;
ELSE
    B_WindowCount := 0;
    B_RejectCount := 0;
    B_LockedOut := FALSE;
    B_WindowComplete := FALSE;
END_IF;

END_FUNCTION_BLOCK
