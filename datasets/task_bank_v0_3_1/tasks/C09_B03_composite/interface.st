FUNCTION_BLOCK C09_B03_composite
VAR_INPUT
    A_FaultA : BOOL;
    A_FaultB : BOOL;
    A_FaultC : BOOL;
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
    A_AnyFault : BOOL;
    A_LockedOut : BOOL;
    A_FirstFault : INT;
    B_Alarm : BOOL;
    B_Disagreeing : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
