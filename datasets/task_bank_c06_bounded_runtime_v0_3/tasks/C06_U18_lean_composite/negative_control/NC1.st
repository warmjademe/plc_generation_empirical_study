FUNCTION_BLOCK C06_U18_lean_composite
VAR_INPUT
    A_AddItem : BOOL;
    A_RemoveItem : BOOL;
    A_Reset : BOOL;
    A_Capacity : INT;
    B_S1 : BOOL;
    B_S2 : BOOL;
    B_S3 : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Count : INT;
    A_Empty : BOOL;
    A_Full : BOOL;
    A_Conflict : BOOL;
    B_Vote : BOOL;
    B_Unanimous : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PrevAdd : BOOL := FALSE;
    A_PrevRemove : BOOL := FALSE;
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
    B_Vote := (B_S1 AND B_S2) OR (B_S1 AND B_S3) OR (B_S2 AND B_S3);
    B_Unanimous := (B_S1 AND B_S2 AND B_S3) OR ((NOT B_S1) AND (NOT B_S2) AND (NOT B_S3));
ELSE
    B_Vote := FALSE;
    B_Unanimous := FALSE;
END_IF;

END_FUNCTION_BLOCK
