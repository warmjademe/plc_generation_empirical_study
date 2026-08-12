FUNCTION_BLOCK C02_M02_local_remote_latch
VAR_INPUT
    RemoteMode : BOOL;
    LocalStart : BOOL;
    RemoteStart : BOOL;
    Stop : BOOL;
    Permit : BOOL;
END_VAR
VAR_OUTPUT
    Running : BOOL;
    SelectedStart : BOOL;
END_VAR
END_FUNCTION_BLOCK
