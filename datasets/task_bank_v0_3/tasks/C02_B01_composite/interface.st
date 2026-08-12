FUNCTION_BLOCK C02_B01_composite
VAR_INPUT
    A_Start : BOOL;
    A_Stop : BOOL;
    A_Fault : BOOL;
    A_Reset : BOOL;
    A_Permit : BOOL;
    B_PowerOK : BOOL;
    B_SafetyOK : BOOL;
    B_Start : BOOL;
    B_Stop : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Running : BOOL;
    A_LockedOut : BOOL;
    B_Running : BOOL;
    B_RestartInhibit : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
