FUNCTION_BLOCK C06_B11_composite
VAR_INPUT
    A_Item : BOOL;
    A_Reset : BOOL;
    A_Target : INT;
    A_Enable : BOOL;
    B_AddItem : BOOL;
    B_RemoveItem : BOOL;
    B_Reset : BOOL;
    B_Capacity : INT;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Count : INT;
    A_BatchDone : BOOL;
    A_Accepted : BOOL;
    B_Count : INT;
    B_Empty : BOOL;
    B_Full : BOOL;
    B_Conflict : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PrevItem : BOOL := FALSE;
    B_PrevAdd : BOOL := FALSE;
    B_PrevRemove : BOOL := FALSE;
END_VAR

A_Accepted := FALSE;
IF A_Reset THEN
    A_Count := 0;
ELSIF A_Enable AND A_Item AND (NOT A_PrevItem) AND (A_Count < A_Target) THEN
    A_Count := A_Count + 1;
    A_Accepted := FALSE;
END_IF;
A_BatchDone := A_Count >= A_Target;
A_PrevItem := A_Item;

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
