FUNCTION_BLOCK C06_B13_composite
VAR_INPUT
    A_AddItem : BOOL;
    A_RemoveItem : BOOL;
    A_Reset : BOOL;
    A_Capacity : INT;
    B_GoodPart : BOOL;
    B_RejectPart : BOOL;
    B_Reset : BOOL;
    B_BatchTarget : INT;
    B_RejectLimit : INT;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Count : INT;
    A_Empty : BOOL;
    A_Full : BOOL;
    A_Conflict : BOOL;
    B_GoodCount : INT;
    B_RejectCount : INT;
    B_BatchDone : BOOL;
    B_QualityFault : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PrevAdd : BOOL := FALSE;
    A_PrevRemove : BOOL := FALSE;
    B_PrevGood : BOOL := FALSE;
    B_PrevReject : BOOL := FALSE;
END_VAR

A_Conflict := FALSE;
IF A_Reset THEN
    A_Count := 0;
ELSIF A_AddItem AND (NOT A_PrevAdd) AND A_RemoveItem AND (NOT A_PrevRemove) THEN
    A_Conflict := TRUE;
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
CrossBlocked := FALSE;

IF SubsystemBEnable AND CrossReady THEN
    IF B_Reset THEN
        B_GoodCount := 0;
        B_RejectCount := 0;
        B_QualityFault := FALSE;
    ELSE
        IF B_RejectPart AND (NOT B_PrevReject) THEN
            B_RejectCount := B_RejectCount + 1;
        ELSIF B_GoodPart AND (NOT B_PrevGood) THEN
            B_GoodCount := B_GoodCount + 1;
        END_IF;
        IF B_RejectCount >= B_RejectLimit THEN
            B_QualityFault := TRUE;
        END_IF;
    END_IF;
    B_BatchDone := (B_GoodCount + B_RejectCount) >= B_BatchTarget;
    B_PrevGood := B_GoodPart;
    B_PrevReject := B_RejectPart;
ELSE
    B_GoodCount := 0;
    B_RejectCount := 0;
    B_BatchDone := FALSE;
    B_QualityFault := FALSE;
END_IF;

END_FUNCTION_BLOCK
