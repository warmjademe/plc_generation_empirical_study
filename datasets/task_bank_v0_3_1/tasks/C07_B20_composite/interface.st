FUNCTION_BLOCK C07_B20_composite
VAR_INPUT
    A_SensorA : REAL;
    A_SensorB : REAL;
    A_ValidA : BOOL;
    A_ValidB : BOOL;
    A_Enable : BOOL;
    A_MaxDifference : REAL;
    A_MaxRate : REAL;
    A_Reset : BOOL;
    B_Temperature : REAL;
    B_LowThreshold : REAL;
    B_HighThreshold : REAL;
    B_Enable : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_ProcessValue : REAL;
    A_ValidOutput : BOOL;
    A_Degraded : BOOL;
    A_Disagree : BOOL;
    A_RateTrip : BOOL;
    B_Heater : BOOL;
    B_ConfigError : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
