FUNCTION_BLOCK C04_B02_composite
VAR_INPUT
    A_Event : BOOL;
    A_Qualify : BOOL;
    A_Reset : BOOL;
    A_MaxCount : INT;
    B_Signal : BOOL;
    B_Arm : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Count : INT;
    A_AcceptedPulse : BOOL;
    A_AtLimit : BOOL;
    B_Pulse : BOOL;
    B_Armed : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
