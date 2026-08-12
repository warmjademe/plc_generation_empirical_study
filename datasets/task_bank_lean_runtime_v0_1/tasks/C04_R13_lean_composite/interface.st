FUNCTION_BLOCK C04_R13_lean_composite
VAR_INPUT
    A_Signal : BOOL;
    A_Arm : BOOL;
    B_S1 : BOOL;
    B_S2 : BOOL;
    B_S3 : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Pulse : BOOL;
    A_Armed : BOOL;
    B_Vote : BOOL;
    B_Unanimous : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
