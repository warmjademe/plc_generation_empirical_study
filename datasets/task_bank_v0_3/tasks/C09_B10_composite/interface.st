FUNCTION_BLOCK C09_B10_composite
VAR_INPUT
    A_Value : REAL;
    A_HighLimit : REAL;
    A_HighHighLimit : REAL;
    A_Reset : BOOL;
    B_WarningCondition : BOOL;
    B_TripCondition : BOOL;
    B_Enable : BOOL;
    B_Acknowledge : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_HighAlarm : BOOL;
    A_HighHighAlarm : BOOL;
    A_Shutdown : BOOL;
    B_Warning : BOOL;
    B_Trip : BOOL;
    B_Unacked : BOOL;
    B_LockedOut : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
