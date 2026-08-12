FUNCTION_BLOCK C06_V10_lean_composite
VAR_INPUT
    A_ChA : BOOL;
    A_ChB : BOOL;
    A_TestMode : BOOL;
    A_TestPermit : BOOL;
    A_ProcessRequest : BOOL;
    B_ItemPulse : BOOL;
    B_Rejected : BOOL;
    B_Stop : BOOL;
    B_Reset : BOOL;
    B_Target : INT;
    B_RejectLimit : INT;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_SafeEnable : BOOL;
    A_Disagree : BOOL;
    A_TestActive : BOOL;
    B_AcceptedCount : INT;
    B_RejectCount : INT;
    B_ConsecutiveRejects : INT;
    B_Complete : BOOL;
    B_LockedOut : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    B_PrevItem : BOOL;
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
    IF B_Reset AND B_Stop AND (NOT B_ItemPulse) THEN
        B_AcceptedCount := 0;
        B_RejectCount := 0;
        B_ConsecutiveRejects := 0;
        B_Complete := FALSE;
        B_LockedOut := FALSE;
    ELSIF B_RejectLimit <= 0 THEN
        B_LockedOut := TRUE;
    ELSIF B_ItemPulse AND (NOT B_PrevItem) AND (NOT B_Stop) AND (NOT B_Complete) AND (NOT B_LockedOut) THEN
        IF B_Rejected THEN
            B_RejectCount := B_RejectCount + 1;
            B_ConsecutiveRejects := B_ConsecutiveRejects + 1;
            IF B_ConsecutiveRejects >= B_RejectLimit THEN B_LockedOut := TRUE; END_IF;
        ELSE
            B_AcceptedCount := B_AcceptedCount + 1;
            B_ConsecutiveRejects := 0;
            IF (B_Target > 0) AND (B_AcceptedCount >= B_Target) THEN B_Complete := TRUE; END_IF;
        END_IF;
    END_IF;
    B_PrevItem := B_ItemPulse;
ELSE
    B_AcceptedCount := 0;
    B_RejectCount := 0;
    B_ConsecutiveRejects := 0;
    B_Complete := FALSE;
    B_LockedOut := FALSE;
END_IF;

END_FUNCTION_BLOCK
