FUNCTION_BLOCK C09_M01_high_high_alarm_priority
VAR_INPUT
    Value : REAL;
    HighLimit : REAL;
    HighHighLimit : REAL;
    Reset : BOOL;
END_VAR
VAR_OUTPUT
    HighAlarm : BOOL;
    HighHighAlarm : BOOL;
    Shutdown : BOOL;
END_VAR
END_FUNCTION_BLOCK
