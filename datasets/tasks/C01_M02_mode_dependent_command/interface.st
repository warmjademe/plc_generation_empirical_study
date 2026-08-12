FUNCTION_BLOCK C01_M02_mode_dependent_command
VAR_INPUT
    AutoMode : BOOL;
    AutoDemand : BOOL;
    ManualDemand : BOOL;
    SafetyOK : BOOL;
    Inhibit : BOOL;
END_VAR
VAR_OUTPUT
    Command : BOOL;
    Blocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
