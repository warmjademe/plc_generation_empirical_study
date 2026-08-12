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
END_FUNCTION_BLOCK
