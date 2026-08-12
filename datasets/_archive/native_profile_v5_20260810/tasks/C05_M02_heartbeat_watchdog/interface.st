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
END_FUNCTION_BLOCK
