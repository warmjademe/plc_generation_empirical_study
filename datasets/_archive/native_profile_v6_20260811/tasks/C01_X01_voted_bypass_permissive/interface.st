FUNCTION_BLOCK C01_X01_voted_bypass_permissive
VAR_INPUT
    Ch1 : BOOL;
    Ch2 : BOOL;
    Ch3 : BOOL;
    AutoMode : BOOL;
    AutoRequest : BOOL;
    ManualRequest : BOOL;
    BypassRequest : BOOL;
    BypassPermit : BOOL;
    SafetyOK : BOOL;
    Reset : BOOL;
END_VAR
VAR_OUTPUT
    RunPermit : BOOL;
    Degraded : BOOL;
    BypassActive : BOOL;
    Blocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
