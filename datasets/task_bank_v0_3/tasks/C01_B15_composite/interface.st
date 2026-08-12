FUNCTION_BLOCK C01_B15_composite
VAR_INPUT
    A_AutoMode : BOOL;
    A_AutoDemand : BOOL;
    A_ManualDemand : BOOL;
    A_SafetyOK : BOOL;
    A_Inhibit : BOOL;
    B_S1 : BOOL;
    B_S2 : BOOL;
    B_S3 : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Command : BOOL;
    A_Blocked : BOOL;
    B_Vote : BOOL;
    B_Unanimous : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
