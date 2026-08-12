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

A_SelectedStart := (A_RemoteMode AND A_RemoteStart) OR ((NOT A_RemoteMode) AND A_LocalStart);
IF A_Stop OR (NOT A_Permit) THEN
    A_Running := FALSE;
ELSIF A_SelectedStart THEN
    A_Running := TRUE;
END_IF;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Running THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

IF SubsystemBEnable AND CrossReady THEN
    B_Ready := B_Enable AND (NOT B_Stop);
    IF (NOT B_Enable) OR B_Stop THEN
        B_Running := FALSE;
    ELSIF B_Start AND B_Ready THEN
        B_Running := TRUE;
    END_IF;
ELSE
    B_Running := FALSE;
    B_Ready := FALSE;
END_IF;

END_FUNCTION_BLOCK
