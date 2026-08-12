FUNCTION_BLOCK C07_B12_composite
VAR_INPUT
    A_Raw : INT;
    B_SensorA : REAL;
    B_SensorB : REAL;
    B_ValidA : BOOL;
    B_ValidB : BOOL;
    B_Enable : BOOL;
    B_MaxDifference : REAL;
    B_MaxRate : REAL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Engineering : REAL;
    A_UnderRange : BOOL;
    A_OverRange : BOOL;
    B_ProcessValue : REAL;
    B_ValidOutput : BOOL;
    B_Degraded : BOOL;
    B_Disagree : BOOL;
    B_RateTrip : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
