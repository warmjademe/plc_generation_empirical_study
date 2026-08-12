FUNCTION_BLOCK C02_B05_composite
VAR_INPUT
    A_PowerOK : BOOL;
    A_SafetyOK : BOOL;
    A_Start : BOOL;
    A_Stop : BOOL;
    A_Reset : BOOL;
    B_Start : BOOL;
    B_Stop : BOOL;
    B_Fault : BOOL;
    B_Reset : BOOL;
    B_Permit : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Running : BOOL;
    A_RestartInhibit : BOOL;
    B_Running : BOOL;
    B_LockedOut : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
