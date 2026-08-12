FUNCTION_BLOCK C02_M01_enabled_start_stop
VAR_INPUT
    Enable : BOOL;
    Start : BOOL;
    Stop : BOOL;
END_VAR
VAR_OUTPUT
    Running : BOOL;
    Ready : BOOL;
END_VAR

Ready := Enable AND (NOT Stop);
IF (NOT Enable) OR Stop THEN
    Running := FALSE;
ELSIF Start AND Ready THEN
    Running := TRUE;
END_IF;

END_FUNCTION_BLOCK
