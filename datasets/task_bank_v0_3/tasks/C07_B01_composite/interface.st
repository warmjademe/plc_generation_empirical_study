FUNCTION_BLOCK C07_B01_composite
VAR_INPUT
    A_SensorA : REAL;
    A_SensorB : REAL;
    A_ValidA : BOOL;
    A_ValidB : BOOL;
    A_MaxDifference : REAL;
    B_Value : REAL;
    B_Enable : BOOL;
    B_MaxRise : REAL;
    B_MaxFall : REAL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Selected : REAL;
    A_Degraded : BOOL;
    A_Disagree : BOOL;
    A_NoValidSensor : BOOL;
    B_Delta : REAL;
    B_Trip : BOOL;
    B_Ready : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
