FUNCTION_BLOCK C04_S18_lean_composite
VAR_INPUT
    A_AutoMode : BOOL;
    A_AutoDemand : BOOL;
    A_ManualDemand : BOOL;
    A_SafetyOK : BOOL;
    A_Inhibit : BOOL;
    B_Signal : BOOL;
    B_Arm : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Command : BOOL;
    A_Blocked : BOOL;
    B_Pulse : BOOL;
    B_Armed : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
