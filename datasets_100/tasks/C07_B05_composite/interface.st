FUNCTION_BLOCK C07_B05_composite
VAR_INPUT
    A_Value : REAL;
    A_Enable : BOOL;
    A_MaxRise : REAL;
    A_MaxFall : REAL;
    A_Reset : BOOL;
    B_SensorA : REAL;
    B_SensorB : REAL;
    B_ValidA : BOOL;
    B_ValidB : BOOL;
    B_MaxDifference : REAL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Delta : REAL;
    A_Trip : BOOL;
    A_Ready : BOOL;
    B_Selected : REAL;
    B_Degraded : BOOL;
    B_Disagree : BOOL;
    B_NoValidSensor : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
