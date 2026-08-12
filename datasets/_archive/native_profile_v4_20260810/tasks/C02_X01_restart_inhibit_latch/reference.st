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
VAR
    SelectedStart : BOOL;
END_VAR

SelectedStart := (AutoMode AND AutoStart) OR ((NOT AutoMode) AND ManualStart);
RejectedStart := FALSE;
IF Stop OR (NOT Enable) THEN
    Running := FALSE;
ELSIF NOT SafetyOK THEN
    IF Running OR SelectedStart THEN RestartRequired := TRUE; END_IF;
    Running := FALSE;
ELSIF RestartRequired THEN
    Running := FALSE;
    IF SelectedStart THEN RejectedStart := TRUE; END_IF;
    IF Reset AND Enable AND SafetyOK AND (NOT SelectedStart) THEN RestartRequired := FALSE; END_IF;
ELSIF SelectedStart THEN
    Running := TRUE;
END_IF;

END_FUNCTION_BLOCK
