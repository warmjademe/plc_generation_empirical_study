FUNCTION_BLOCK C09_M02_qualified_sensor_disagreement
VAR_INPUT
    SensorA : REAL;
    SensorB : REAL;
    MaxDifference : REAL;
    Enable : BOOL;
    Reset : BOOL;
END_VAR
VAR_OUTPUT
    Alarm : BOOL;
    Disagreeing : BOOL;
END_VAR
VAR
    DisagreeTimer : TON;
END_VAR

Disagreeing := Enable AND (ABS(SensorA - SensorB) > MaxDifference);
DisagreeTimer(IN := Disagreeing, PT := T#300ms);
IF DisagreeTimer.Q THEN
    Alarm := TRUE;
ELSIF Reset AND (NOT Disagreeing) THEN
    Alarm := FALSE;
END_IF;

END_FUNCTION_BLOCK
