FUNCTION_BLOCK C06_W04_lean_composite
VAR_INPUT
    A_Info : BOOL;
    A_Warning : BOOL;
    A_Trip : BOOL;
    A_Emergency : BOOL;
    A_Suppress : BOOL;
    B_AddItem : BOOL;
    B_RemoveItem : BOOL;
    B_Reset : BOOL;
    B_Capacity : INT;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Active : BOOL;
    A_Level : INT;
    B_Count : INT;
    B_Empty : BOOL;
    B_Full : BOOL;
    B_Conflict : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
