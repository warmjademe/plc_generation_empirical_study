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
END_FUNCTION_BLOCK
