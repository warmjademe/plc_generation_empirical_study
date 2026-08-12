FUNCTION_BLOCK C02_X01_restart_inhibit_latch
VAR_INPUT
    AutoMode : BOOL;
    AutoStart : BOOL;
    ManualStart : BOOL;
    Stop : BOOL;
    Enable : BOOL;
    SafetyOK : BOOL;
    Reset : BOOL;
END_VAR
VAR_OUTPUT
    Running : BOOL;
    RestartRequired : BOOL;
    RejectedStart : BOOL;
END_VAR
END_FUNCTION_BLOCK
