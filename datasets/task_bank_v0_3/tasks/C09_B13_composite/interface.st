FUNCTION_BLOCK C09_B13_composite
VAR_INPUT
    A_SensorA : REAL;
    A_SensorB : REAL;
    A_MaxDifference : REAL;
    A_Enable : BOOL;
    A_Reset : BOOL;
    B_FaultA : BOOL;
    B_FaultB : BOOL;
    B_FaultC : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Alarm : BOOL;
    A_Disagreeing : BOOL;
    B_AnyFault : BOOL;
    B_LockedOut : BOOL;
    B_FirstFault : INT;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
