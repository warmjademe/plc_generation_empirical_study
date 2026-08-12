FUNCTION_BLOCK C04_S11_lean_composite
VAR_INPUT
    A_S1 : BOOL;
    A_S2 : BOOL;
    A_S3 : BOOL;
    B_Event : BOOL;
    B_Qualify : BOOL;
    B_Reset : BOOL;
    B_MaxCount : INT;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Vote : BOOL;
    A_Unanimous : BOOL;
    B_Count : INT;
    B_AcceptedPulse : BOOL;
    B_AtLimit : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
