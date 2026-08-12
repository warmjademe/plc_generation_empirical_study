FUNCTION_BLOCK C07_X01_plausible_rate_limited_fusion
VAR_INPUT
    SensorA : REAL;
    SensorB : REAL;
    ValidA : BOOL;
    ValidB : BOOL;
    Enable : BOOL;
    MaxDifference : REAL;
    MaxRate : REAL;
    Reset : BOOL;
END_VAR
VAR_OUTPUT
    ProcessValue : REAL;
    ValidOutput : BOOL;
    Degraded : BOOL;
    Disagree : BOOL;
    RateTrip : BOOL;
END_VAR
END_FUNCTION_BLOCK
