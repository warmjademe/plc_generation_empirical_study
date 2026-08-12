FUNCTION_BLOCK C06_W15_lean_composite
VAR_INPUT
    A_S1 : BOOL;
    A_S2 : BOOL;
    A_S3 : BOOL;
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
    A_Vote : BOOL;
    A_Unanimous : BOOL;
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

A_Vote := (A_S1 AND A_S2) OR (A_S1 AND A_S3) OR (A_S2 AND A_S3);
A_Unanimous := (A_S1 AND A_S2 AND A_S3) OR ((NOT A_S1) AND (NOT A_S2) AND (NOT A_S3));

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Vote THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := FALSE;

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
