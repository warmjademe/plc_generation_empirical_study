FUNCTION_BLOCK C07_B13_composite
VAR_INPUT
    A_Temperature : REAL;
    A_LowThreshold : REAL;
    A_HighThreshold : REAL;
    A_Enable : BOOL;
    B_SensorA : REAL;
    B_SensorB : REAL;
    B_ValidA : BOOL;
    B_ValidB : BOOL;
    B_MaxDifference : REAL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Heater : BOOL;
    A_ConfigError : BOOL;
    B_Selected : REAL;
    B_Degraded : BOOL;
    B_Disagree : BOOL;
    B_NoValidSensor : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
