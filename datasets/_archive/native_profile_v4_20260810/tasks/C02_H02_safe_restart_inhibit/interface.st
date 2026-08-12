FUNCTION_BLOCK C02_H02_safe_restart_inhibit
VAR_INPUT
    PowerOK : BOOL;
    SafetyOK : BOOL;
    Start : BOOL;
    Stop : BOOL;
    Reset : BOOL;
END_VAR
VAR_OUTPUT
    Running : BOOL;
    RestartInhibit : BOOL;
END_VAR
END_FUNCTION_BLOCK
