FUNCTION_BLOCK C09_B19_composite
VAR_INPUT
    A_WarningCondition : BOOL;
    A_TripCondition : BOOL;
    A_Enable : BOOL;
    A_Shelve : BOOL;
    A_Acknowledge : BOOL;
    A_Reset : BOOL;
    B_Value : REAL;
    B_HighLimit : REAL;
    B_HighHighLimit : REAL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Warning : BOOL;
    A_Trip : BOOL;
    A_Unacked : BOOL;
    A_Shelved : BOOL;
    A_LockedOut : BOOL;
    B_HighAlarm : BOOL;
    B_HighHighAlarm : BOOL;
    B_Shutdown : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
