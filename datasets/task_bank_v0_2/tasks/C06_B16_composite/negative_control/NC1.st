FUNCTION_BLOCK C06_B16_composite
VAR_INPUT
    A_AddItem : BOOL;
    A_RemoveItem : BOOL;
    A_Reset : BOOL;
    A_Capacity : INT;
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
    A_Count : INT;
    A_Empty : BOOL;
    A_Full : BOOL;
    A_Conflict : BOOL;
    B_AcceptedCount : INT;
    B_RejectCount : INT;
    B_ConsecutiveRejects : INT;
    B_Complete : BOOL;
    B_LockedOut : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PrevAdd : BOOL := FALSE;
    A_PrevRemove : BOOL := FALSE;
    B_PrevItem : BOOL;
END_VAR

A_Conflict := FALSE;
IF A_Reset THEN
    A_Count := 0;
ELSIF A_AddItem AND (NOT A_PrevAdd) AND A_RemoveItem AND (NOT A_PrevRemove) THEN
    A_Conflict := FALSE;
ELSIF A_AddItem AND (NOT A_PrevAdd) AND (A_Count < A_Capacity) THEN
    A_Count := A_Count + 1;
ELSIF A_RemoveItem AND (NOT A_PrevRemove) AND (A_Count > 0) THEN
    A_Count := A_Count - 1;
END_IF;
A_Empty := A_Count = 0;
A_Full := A_Count >= A_Capacity;
A_PrevAdd := A_AddItem;
A_PrevRemove := A_RemoveItem;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Empty THEN
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
