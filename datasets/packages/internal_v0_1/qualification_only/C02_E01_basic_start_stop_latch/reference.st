FUNCTION_BLOCK C02_E01_basic_start_stop_latch
VAR_INPUT
    Start : BOOL;
    Stop : BOOL;
END_VAR
VAR_OUTPUT
    Running : BOOL;
END_VAR

IF Stop THEN
    Running := FALSE;
ELSIF Start THEN
    Running := TRUE;
END_IF;

END_FUNCTION_BLOCK
