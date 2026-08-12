FUNCTION_BLOCK C10_H02_fair_resource_arbiter
VAR_INPUT
    RequestA : BOOL;
    RequestB : BOOL;
    Done : BOOL;
    Emergency : BOOL;
    Reset : BOOL;
END_VAR
VAR_OUTPUT
    GrantA : BOOL;
    GrantB : BOOL;
    Busy : BOOL;
    Turn : INT;
    LockedOut : BOOL;
END_VAR
END_FUNCTION_BLOCK
