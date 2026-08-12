FUNCTION_BLOCK C06_B15_composite
VAR_INPUT
    A_AddItem : BOOL;
    A_RemoveItem : BOOL;
    A_Reset : BOOL;
    A_Capacity : INT;
    B_Item : BOOL;
    B_Reset : BOOL;
    B_Target : INT;
    B_Enable : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Count : INT;
    A_Empty : BOOL;
    A_Full : BOOL;
    A_Conflict : BOOL;
    B_Count : INT;
    B_BatchDone : BOOL;
    B_Accepted : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PrevAdd : BOOL := FALSE;
    A_PrevRemove : BOOL := FALSE;
    B_PrevItem : BOOL := FALSE;
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
    B_Accepted := FALSE;
    IF B_Reset THEN
        B_Count := 0;
    ELSIF B_Enable AND B_Item AND (NOT B_PrevItem) AND (B_Count < B_Target) THEN
        B_Count := B_Count + 1;
        B_Accepted := TRUE;
    END_IF;
    B_BatchDone := B_Count >= B_Target;
    B_PrevItem := B_Item;
ELSE
    B_Count := 0;
    B_BatchDone := FALSE;
    B_Accepted := FALSE;
END_IF;

END_FUNCTION_BLOCK
