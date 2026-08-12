FUNCTION_BLOCK C02_B16_composite
VAR_INPUT
    A_RemoteMode : BOOL;
    A_LocalStart : BOOL;
    A_RemoteStart : BOOL;
    A_Stop : BOOL;
    A_Permit : BOOL;
    B_AutoMode : BOOL;
    B_AutoStart : BOOL;
    B_ManualStart : BOOL;
    B_Stop : BOOL;
    B_Enable : BOOL;
    B_SafetyOK : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Running : BOOL;
    A_SelectedStart : BOOL;
    B_Running : BOOL;
    B_RestartRequired : BOOL;
    B_RejectedStart : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
