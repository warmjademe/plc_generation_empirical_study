FUNCTION_BLOCK C02_H01_fault_lockout_reset
VAR_INPUT
    Start : BOOL;
    Stop : BOOL;
    Fault : BOOL;
    Reset : BOOL;
    Permit : BOOL;
END_VAR
VAR_OUTPUT
    Running : BOOL;
    LockedOut : BOOL;
END_VAR

IF Fault THEN
    LockedOut := FALSE;
    Running := FALSE;
ELSIF Reset AND (NOT Start) THEN
    LockedOut := FALSE;
END_IF;

IF LockedOut OR Stop OR (NOT Permit) THEN
    Running := FALSE;
ELSIF Start THEN
    Running := TRUE;
END_IF;

END_FUNCTION_BLOCK
