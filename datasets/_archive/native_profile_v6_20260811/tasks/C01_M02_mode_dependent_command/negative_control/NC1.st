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

Command := ((AutoMode OR AutoDemand) OR ((NOT AutoMode) AND ManualDemand))
           AND SafetyOK AND (NOT Inhibit);
Blocked := ((AutoMode AND AutoDemand) OR ((NOT AutoMode) AND ManualDemand))
           AND ((NOT SafetyOK) OR Inhibit);

END_FUNCTION_BLOCK
