FUNCTION_BLOCK C04_R02_lean_composite
VAR_INPUT
    A_Info : BOOL;
    A_Warning : BOOL;
    A_Trip : BOOL;
    A_Emergency : BOOL;
    A_Suppress : BOOL;
    B_EventA : BOOL;
    B_EventB : BOOL;
    B_Arm : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Active : BOOL;
    A_Level : INT;
    B_Captured : BOOL;
    B_Code : INT;
    B_Pulse : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
