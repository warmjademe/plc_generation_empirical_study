FUNCTION_BLOCK C09_B11_composite
VAR_INPUT
    A_Value : REAL;
    A_HighLimit : REAL;
    A_HighHighLimit : REAL;
    A_Reset : BOOL;
    B_SensorA : REAL;
    B_SensorB : REAL;
    B_MaxDifference : REAL;
    B_Enable : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_HighAlarm : BOOL;
    A_HighHighAlarm : BOOL;
    A_Shutdown : BOOL;
    B_Alarm : BOOL;
    B_Disagreeing : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
