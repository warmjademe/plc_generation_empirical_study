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

IF (NOT PowerOK) OR (NOT SafetyOK) THEN
    Running := FALSE;
    RestartInhibit := FALSE;
ELSIF Stop THEN
    Running := FALSE;
ELSIF Reset AND (NOT Start) THEN
    RestartInhibit := FALSE;
ELSIF Start AND (NOT RestartInhibit) THEN
    Running := TRUE;
END_IF;

IF RestartInhibit THEN
    Running := FALSE;
END_IF;

END_FUNCTION_BLOCK
