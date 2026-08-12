FUNCTION_BLOCK C06_U01_lean_composite
VAR_INPUT
    A_GoodPart : BOOL;
    A_RejectPart : BOOL;
    A_Reset : BOOL;
    A_BatchTarget : INT;
    A_RejectLimit : INT;
    B_Info : BOOL;
    B_Warning : BOOL;
    B_Trip : BOOL;
    B_Emergency : BOOL;
    B_Suppress : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_GoodCount : INT;
    A_RejectCount : INT;
    A_BatchDone : BOOL;
    A_QualityFault : BOOL;
    B_Active : BOOL;
    B_Level : INT;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
