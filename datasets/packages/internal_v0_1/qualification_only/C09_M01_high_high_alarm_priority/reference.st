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

IF Value >= HighHighLimit THEN
    HighAlarm := TRUE;
    HighHighAlarm := TRUE;
    Shutdown := TRUE;
ELSIF Value >= HighLimit THEN
    HighAlarm := TRUE;
END_IF;
IF Reset AND (Value < HighLimit) THEN
    HighAlarm := FALSE;
    HighHighAlarm := FALSE;
    Shutdown := FALSE;
END_IF;

END_FUNCTION_BLOCK
