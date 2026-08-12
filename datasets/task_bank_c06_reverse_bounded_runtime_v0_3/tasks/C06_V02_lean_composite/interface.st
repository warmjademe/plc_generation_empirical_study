FUNCTION_BLOCK C06_V02_lean_composite
VAR_INPUT
    A_Info : BOOL;
    A_Warning : BOOL;
    A_Trip : BOOL;
    A_Emergency : BOOL;
    A_Suppress : BOOL;
    B_Inspected : BOOL;
    B_Rejected : BOOL;
    B_Reset : BOOL;
    B_WindowSize : INT;
    B_RejectLimit : INT;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Active : BOOL;
    A_Level : INT;
    B_WindowCount : INT;
    B_RejectCount : INT;
    B_LockedOut : BOOL;
    B_WindowComplete : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
