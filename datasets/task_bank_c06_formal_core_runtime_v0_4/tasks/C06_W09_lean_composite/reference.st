FUNCTION_BLOCK C06_W09_lean_composite
VAR_INPUT
    A_ChA : BOOL;
    A_ChB : BOOL;
    A_TestMode : BOOL;
    A_TestPermit : BOOL;
    A_ProcessRequest : BOOL;
    B_AddItem : BOOL;
    B_RemoveItem : BOOL;
    B_Reset : BOOL;
    B_Capacity : INT;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_SafeEnable : BOOL;
    A_Disagree : BOOL;
    A_TestActive : BOOL;
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
