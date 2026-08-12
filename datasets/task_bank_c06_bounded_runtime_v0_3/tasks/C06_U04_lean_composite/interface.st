FUNCTION_BLOCK C06_U04_lean_composite
VAR_INPUT
    A_GoodPart : BOOL;
    A_RejectPart : BOOL;
    A_Reset : BOOL;
    A_BatchTarget : INT;
    A_RejectLimit : INT;
    B_AutoMode : BOOL;
    B_AutoDemand : BOOL;
    B_ManualDemand : BOOL;
    B_SafetyOK : BOOL;
    B_Inhibit : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_GoodCount : INT;
    A_RejectCount : INT;
    A_BatchDone : BOOL;
    A_QualityFault : BOOL;
    B_Command : BOOL;
    B_Blocked : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
