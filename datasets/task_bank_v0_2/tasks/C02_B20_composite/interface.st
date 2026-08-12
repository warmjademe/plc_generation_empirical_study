FUNCTION_BLOCK C02_B20_composite
VAR_INPUT
    A_AutoMode : BOOL;
    A_AutoStart : BOOL;
    A_ManualStart : BOOL;
    A_Stop : BOOL;
    A_Enable : BOOL;
    A_SafetyOK : BOOL;
    A_Reset : BOOL;
    B_RemoteMode : BOOL;
    B_LocalStart : BOOL;
    B_RemoteStart : BOOL;
    B_Stop : BOOL;
    B_Permit : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Running : BOOL;
    A_RestartRequired : BOOL;
    A_RejectedStart : BOOL;
    B_Running : BOOL;
    B_SelectedStart : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
