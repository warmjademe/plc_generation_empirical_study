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

A_Ready := A_Enable AND (NOT A_Stop);
IF (NOT A_Enable) OR A_Stop THEN
    A_Running := FALSE;
ELSIF A_Start AND A_Ready THEN
    A_Running := TRUE;
END_IF;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Running THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

IF SubsystemBEnable AND CrossReady THEN
    B_SelectedStart := (B_RemoteMode AND B_RemoteStart) OR ((NOT B_RemoteMode) AND B_LocalStart);
    IF B_Stop OR (NOT B_Permit) THEN
        B_Running := FALSE;
    ELSIF B_SelectedStart THEN
        B_Running := TRUE;
    END_IF;
ELSE
    B_Running := FALSE;
    B_SelectedStart := FALSE;
END_IF;

END_FUNCTION_BLOCK
