FUNCTION_BLOCK C05_M02_heartbeat_watchdog
VAR_INPUT
    MonitorEnable : BOOL;
    Heartbeat : BOOL;
    Reset : BOOL;
END_VAR
VAR_OUTPUT
    TimedOut : BOOL;
    Healthy : BOOL;
END_VAR
VAR
    Watchdog : TON;
END_VAR

Watchdog(IN := MonitorEnable AND (NOT Heartbeat) AND (NOT TimedOut), PT := T#400ms);
IF Watchdog.Q THEN
    TimedOut := FALSE;
ELSIF Reset AND (NOT MonitorEnable) THEN
    TimedOut := FALSE;
END_IF;
Healthy := MonitorEnable AND (NOT TimedOut);

END_FUNCTION_BLOCK
