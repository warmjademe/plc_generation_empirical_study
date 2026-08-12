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

SelectedStart := (RemoteMode AND RemoteStart) OR ((NOT RemoteMode) AND LocalStart);
IF Stop OR (NOT Permit) THEN
    Running := FALSE;
ELSIF SelectedStart THEN
    Running := TRUE;
END_IF;

END_FUNCTION_BLOCK
