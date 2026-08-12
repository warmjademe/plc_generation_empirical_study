FUNCTION_BLOCK C02_B11_composite
VAR_INPUT
    A_Enable : BOOL;
    A_Start : BOOL;
    A_Stop : BOOL;
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
    A_Ready : BOOL;
    B_Running : BOOL;
    B_SelectedStart : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
