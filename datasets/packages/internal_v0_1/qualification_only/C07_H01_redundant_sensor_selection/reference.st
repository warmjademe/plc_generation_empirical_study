FUNCTION_BLOCK C07_H01_redundant_sensor_selection
VAR_INPUT
    SensorA : REAL;
    SensorB : REAL;
    ValidA : BOOL;
    ValidB : BOOL;
    MaxDifference : REAL;
END_VAR
VAR_OUTPUT
    Selected : REAL;
    Degraded : BOOL;
    Disagree : BOOL;
    NoValidSensor : BOOL;
END_VAR

Degraded := FALSE;
Disagree := FALSE;
NoValidSensor := FALSE;
IF ValidA AND ValidB THEN
    IF ABS(SensorA - SensorB) <= MaxDifference THEN
        Selected := (SensorA + SensorB) / 2.0;
    ELSE
        Disagree := TRUE;
    END_IF;
ELSIF ValidA THEN
    Selected := SensorA;
    Degraded := TRUE;
ELSIF ValidB THEN
    Selected := SensorB;
    Degraded := TRUE;
ELSE
    NoValidSensor := TRUE;
END_IF;

END_FUNCTION_BLOCK
