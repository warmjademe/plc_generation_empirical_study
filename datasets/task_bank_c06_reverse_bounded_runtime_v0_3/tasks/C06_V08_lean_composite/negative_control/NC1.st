FUNCTION_BLOCK C06_V08_lean_composite
VAR_INPUT
    A_ChA : BOOL;
    A_ChB : BOOL;
    A_TestMode : BOOL;
    A_TestPermit : BOOL;
    A_ProcessRequest : BOOL;
    B_Item : BOOL;
    B_Reset : BOOL;
    B_Target : INT;
    B_Enable : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_SafeEnable : BOOL;
    A_Disagree : BOOL;
    A_TestActive : BOOL;
    B_Count : INT;
    B_BatchDone : BOOL;
    B_Accepted : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    B_PrevItem : BOOL := FALSE;
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
CrossBlocked := FALSE;

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
