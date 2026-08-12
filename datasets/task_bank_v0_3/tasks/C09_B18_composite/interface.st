FUNCTION_BLOCK C09_B18_composite
VAR_INPUT
    A_WarningCondition : BOOL;
    A_TripCondition : BOOL;
    A_Enable : BOOL;
    A_Shelve : BOOL;
    A_Acknowledge : BOOL;
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
    A_Warning : BOOL;
    A_Trip : BOOL;
    A_Unacked : BOOL;
    A_Shelved : BOOL;
    A_LockedOut : BOOL;
    B_Warning : BOOL;
    B_Trip : BOOL;
    B_Unacked : BOOL;
    B_LockedOut : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
