FUNCTION_BLOCK C02_B09_composite
VAR_INPUT
    A_Enable : BOOL;
    A_Start : BOOL;
    A_Stop : BOOL;
    B_Start : BOOL;
    B_Stop : BOOL;
    B_Fault : BOOL;
    B_Reset : BOOL;
    B_Permit : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Running : BOOL;
    A_Ready : BOOL;
    B_Running : BOOL;
    B_LockedOut : BOOL;
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
CrossBlocked := FALSE;

IF SubsystemBEnable AND CrossReady THEN
    IF B_Fault THEN
        B_LockedOut := TRUE;
        B_Running := FALSE;
    ELSIF B_Reset AND (NOT B_Start) THEN
        B_LockedOut := FALSE;
    END_IF;

    IF B_LockedOut OR B_Stop OR (NOT B_Permit) THEN
        B_Running := FALSE;
    ELSIF B_Start THEN
        B_Running := TRUE;
    END_IF;
ELSE
    B_Running := FALSE;
    B_LockedOut := FALSE;
END_IF;

END_FUNCTION_BLOCK
