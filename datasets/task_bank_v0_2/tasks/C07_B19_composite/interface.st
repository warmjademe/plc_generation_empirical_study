FUNCTION_BLOCK C07_B19_composite
VAR_INPUT
    A_SensorA : REAL;
    A_SensorB : REAL;
    A_ValidA : BOOL;
    A_ValidB : BOOL;
    A_Enable : BOOL;
    A_MaxDifference : REAL;
    A_MaxRate : REAL;
    A_Reset : BOOL;
    B_Raw : INT;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_ProcessValue : REAL;
    A_ValidOutput : BOOL;
    A_Degraded : BOOL;
    A_Disagree : BOOL;
    A_RateTrip : BOOL;
    B_Engineering : REAL;
    B_UnderRange : BOOL;
    B_OverRange : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
