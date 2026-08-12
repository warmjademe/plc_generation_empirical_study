FUNCTION_BLOCK C06_R12_lean_composite
VAR_INPUT
    A_Item : BOOL;
    A_Reset : BOOL;
    A_Target : INT;
    A_Enable : BOOL;
    B_ChA : BOOL;
    B_ChB : BOOL;
    B_TestMode : BOOL;
    B_TestPermit : BOOL;
    B_ProcessRequest : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Count : INT;
    A_BatchDone : BOOL;
    A_Accepted : BOOL;
    B_SafeEnable : BOOL;
    B_Disagree : BOOL;
    B_TestActive : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PrevItem : BOOL := FALSE;
END_VAR

A_Accepted := FALSE;
IF A_Reset THEN
    A_Count := 0;
ELSIF A_Enable AND A_Item AND (NOT A_PrevItem) AND (A_Count < A_Target) THEN
    A_Count := A_Count + 1;
    A_Accepted := TRUE;
END_IF;
A_BatchDone := A_Count >= A_Target;
A_PrevItem := A_Item;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_BatchDone THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := FALSE;

IF SubsystemBEnable AND CrossReady THEN
    B_Disagree := B_ChA <> B_ChB;
    B_TestActive := B_TestMode AND B_TestPermit;
    IF B_TestMode THEN
        B_SafeEnable := B_ProcessRequest AND B_TestPermit AND B_ChA;
    ELSE
        B_SafeEnable := B_ProcessRequest AND B_ChA AND B_ChB;
    END_IF;
ELSE
    B_SafeEnable := FALSE;
    B_Disagree := FALSE;
    B_TestActive := FALSE;
END_IF;

END_FUNCTION_BLOCK
