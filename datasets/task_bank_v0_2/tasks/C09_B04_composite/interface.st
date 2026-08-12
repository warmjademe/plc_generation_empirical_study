FUNCTION_BLOCK C09_B04_composite
VAR_INPUT
    A_FaultA : BOOL;
    A_FaultB : BOOL;
    A_FaultC : BOOL;
    A_Reset : BOOL;
    B_WarningCondition : BOOL;
    B_TripCondition : BOOL;
    B_Enable : BOOL;
    B_Shelve : BOOL;
    B_Acknowledge : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_AnyFault : BOOL;
    A_LockedOut : BOOL;
    A_FirstFault : INT;
    B_Warning : BOOL;
    B_Trip : BOOL;
    B_Unacked : BOOL;
    B_Shelved : BOOL;
    B_LockedOut : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
