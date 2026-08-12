FUNCTION_BLOCK C06_U23_lean_composite
VAR_INPUT
    A_ItemPulse : BOOL;
    A_Rejected : BOOL;
    A_Stop : BOOL;
    A_Reset : BOOL;
    A_Target : INT;
    A_RejectLimit : INT;
    B_S1 : BOOL;
    B_S2 : BOOL;
    B_S3 : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_AcceptedCount : INT;
    A_RejectCount : INT;
    A_ConsecutiveRejects : INT;
    A_Complete : BOOL;
    A_LockedOut : BOOL;
    B_Vote : BOOL;
    B_Unanimous : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PrevItem : BOOL;
END_VAR

IF A_Reset AND A_Stop AND (NOT A_ItemPulse) THEN
    A_AcceptedCount := 0;
    A_RejectCount := 0;
    A_ConsecutiveRejects := 0;
    A_Complete := FALSE;
    A_LockedOut := FALSE;
ELSIF A_RejectLimit <= 0 THEN
    A_LockedOut := TRUE;
ELSIF A_ItemPulse AND (NOT A_PrevItem) AND (NOT A_Stop) AND (NOT A_Complete) AND (NOT A_LockedOut) THEN
    IF A_Rejected THEN
        A_RejectCount := A_RejectCount + 1;
        A_ConsecutiveRejects := A_ConsecutiveRejects + 1;
        IF A_ConsecutiveRejects >= A_RejectLimit THEN A_LockedOut := TRUE; END_IF;
    ELSE
        A_AcceptedCount := A_AcceptedCount + 1;
        A_ConsecutiveRejects := 0;
        IF (A_Target > 0) AND (A_AcceptedCount >= A_Target) THEN A_Complete := TRUE; END_IF;
    END_IF;
END_IF;
A_PrevItem := A_ItemPulse;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Complete THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := FALSE;

IF SubsystemBEnable AND CrossReady THEN
    B_Vote := (B_S1 AND B_S2) OR (B_S1 AND B_S3) OR (B_S2 AND B_S3);
    B_Unanimous := (B_S1 AND B_S2 AND B_S3) OR ((NOT B_S1) AND (NOT B_S2) AND (NOT B_S3));
ELSE
    B_Vote := FALSE;
    B_Unanimous := FALSE;
END_IF;

END_FUNCTION_BLOCK
