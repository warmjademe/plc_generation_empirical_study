FUNCTION_BLOCK C02_B02_composite
VAR_INPUT
    A_Start : BOOL;
    A_Stop : BOOL;
    A_Fault : BOOL;
    A_Reset : BOOL;
    A_Permit : BOOL;
    B_Enable : BOOL;
    B_Start : BOOL;
    B_Stop : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Running : BOOL;
    A_LockedOut : BOOL;
    B_Running : BOOL;
    B_Ready : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR

IF A_Fault THEN
    A_LockedOut := FALSE;
    A_Running := FALSE;
ELSIF A_Reset AND (NOT A_Start) THEN
    A_LockedOut := FALSE;
END_IF;

IF A_LockedOut OR A_Stop OR (NOT A_Permit) THEN
    A_Running := FALSE;
ELSIF A_Start THEN
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
