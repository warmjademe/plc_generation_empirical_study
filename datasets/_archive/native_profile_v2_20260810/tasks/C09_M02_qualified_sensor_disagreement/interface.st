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
END_FUNCTION_BLOCK
