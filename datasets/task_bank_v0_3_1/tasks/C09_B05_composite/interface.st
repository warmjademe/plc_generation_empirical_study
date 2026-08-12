FUNCTION_BLOCK C09_B05_composite
VAR_INPUT
    A_WarningCondition : BOOL;
    A_TripCondition : BOOL;
    A_Enable : BOOL;
    A_Acknowledge : BOOL;
    A_Reset : BOOL;
    B_FaultA : BOOL;
    B_FaultB : BOOL;
    B_FaultC : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Warning : BOOL;
    A_Trip : BOOL;
    A_Unacked : BOOL;
    A_LockedOut : BOOL;
    B_AnyFault : BOOL;
    B_LockedOut : BOOL;
    B_FirstFault : INT;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
