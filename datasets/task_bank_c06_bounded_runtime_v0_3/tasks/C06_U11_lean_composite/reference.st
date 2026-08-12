FUNCTION_BLOCK C06_U11_lean_composite
VAR_INPUT
    A_Item : BOOL;
    A_Reset : BOOL;
    A_Target : INT;
    A_Enable : BOOL;
    B_Info : BOOL;
    B_Warning : BOOL;
    B_Trip : BOOL;
    B_Emergency : BOOL;
    B_Suppress : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Count : INT;
    A_BatchDone : BOOL;
    A_Accepted : BOOL;
    B_Active : BOOL;
    B_Level : INT;
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
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

IF SubsystemBEnable AND CrossReady THEN
    IF B_Emergency THEN
        B_Level := 4;
        B_Active := TRUE;
    ELSIF B_Suppress THEN
        B_Level := 0;
        B_Active := FALSE;
    ELSIF B_Trip THEN
        B_Level := 3;
        B_Active := TRUE;
    ELSIF B_Warning THEN
        B_Level := 2;
        B_Active := TRUE;
    ELSIF B_Info THEN
        B_Level := 1;
        B_Active := TRUE;
    ELSE
        B_Level := 0;
        B_Active := FALSE;
    END_IF;
ELSE
    B_Active := FALSE;
    B_Level := 0;
END_IF;

END_FUNCTION_BLOCK
