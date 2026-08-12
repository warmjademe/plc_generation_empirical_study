FUNCTION_BLOCK C04_R01_lean_composite
VAR_INPUT
    A_Info : BOOL;
    A_Warning : BOOL;
    A_Trip : BOOL;
    A_Emergency : BOOL;
    A_Suppress : BOOL;
    B_Event : BOOL;
    B_Qualify : BOOL;
    B_Reset : BOOL;
    B_MaxCount : INT;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Active : BOOL;
    A_Level : INT;
    B_Count : INT;
    B_AcceptedPulse : BOOL;
    B_AtLimit : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
