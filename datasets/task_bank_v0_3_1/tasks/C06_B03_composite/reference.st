FUNCTION_BLOCK C06_B03_composite
VAR_INPUT
    A_GoodPart : BOOL;
    A_RejectPart : BOOL;
    A_Reset : BOOL;
    A_BatchTarget : INT;
    A_RejectLimit : INT;
    B_AddItem : BOOL;
    B_RemoveItem : BOOL;
    B_Reset : BOOL;
    B_Capacity : INT;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_GoodCount : INT;
    A_RejectCount : INT;
    A_BatchDone : BOOL;
    A_QualityFault : BOOL;
    B_Count : INT;
    B_Empty : BOOL;
    B_Full : BOOL;
    B_Conflict : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PrevGood : BOOL := FALSE;
    A_PrevReject : BOOL := FALSE;
    B_PrevAdd : BOOL := FALSE;
    B_PrevRemove : BOOL := FALSE;
END_VAR

IF A_Reset THEN
    A_GoodCount := 0;
    A_RejectCount := 0;
    A_QualityFault := FALSE;
ELSE
    IF A_RejectPart AND (NOT A_PrevReject) THEN
        A_RejectCount := A_RejectCount + 1;
    ELSIF A_GoodPart AND (NOT A_PrevGood) THEN
        A_GoodCount := A_GoodCount + 1;
    END_IF;
    IF A_RejectCount >= A_RejectLimit THEN
        A_QualityFault := TRUE;
    END_IF;
END_IF;
A_BatchDone := (A_GoodCount + A_RejectCount) >= A_BatchTarget;
A_PrevGood := A_GoodPart;
A_PrevReject := A_RejectPart;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_BatchDone THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

IF SubsystemBEnable AND CrossReady THEN
    B_Conflict := FALSE;
    IF B_Reset THEN
        B_Count := 0;
    ELSIF B_AddItem AND (NOT B_PrevAdd) AND B_RemoveItem AND (NOT B_PrevRemove) THEN
        B_Conflict := TRUE;
    ELSIF B_AddItem AND (NOT B_PrevAdd) AND (B_Count < B_Capacity) THEN
        B_Count := B_Count + 1;
    ELSIF B_RemoveItem AND (NOT B_PrevRemove) AND (B_Count > 0) THEN
        B_Count := B_Count - 1;
    END_IF;
    B_Empty := B_Count = 0;
    B_Full := B_Count >= B_Capacity;
    B_PrevAdd := B_AddItem;
    B_PrevRemove := B_RemoveItem;
ELSE
    B_Count := 0;
    B_Empty := FALSE;
    B_Full := FALSE;
    B_Conflict := FALSE;
END_IF;

END_FUNCTION_BLOCK
