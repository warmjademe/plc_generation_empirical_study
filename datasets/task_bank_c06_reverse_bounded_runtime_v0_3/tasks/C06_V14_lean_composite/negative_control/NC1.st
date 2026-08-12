FUNCTION_BLOCK C06_V14_lean_composite
VAR_INPUT
    A_S1 : BOOL;
    A_S2 : BOOL;
    A_S3 : BOOL;
    B_AddItem : BOOL;
    B_RemoveItem : BOOL;
    B_Reset : BOOL;
    B_Capacity : INT;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Vote : BOOL;
    A_Unanimous : BOOL;
    B_Count : INT;
    B_Empty : BOOL;
    B_Full : BOOL;
    B_Conflict : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    B_PrevAdd : BOOL := FALSE;
    B_PrevRemove : BOOL := FALSE;
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
