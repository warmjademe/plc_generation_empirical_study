FUNCTION_BLOCK C02_B15_composite
VAR_INPUT
    A_RemoteMode : BOOL;
    A_LocalStart : BOOL;
    A_RemoteStart : BOOL;
    A_Stop : BOOL;
    A_Permit : BOOL;
    B_Enable : BOOL;
    B_Start : BOOL;
    B_Stop : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Running : BOOL;
    A_SelectedStart : BOOL;
    B_Running : BOOL;
    B_Ready : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
