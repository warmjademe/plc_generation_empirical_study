FUNCTION_BLOCK C10_B05_composite
VAR_INPUT
    A_RequestA : BOOL;
    A_RequestB : BOOL;
    A_Done : BOOL;
    A_Emergency : BOOL;
    A_Reset : BOOL;
    B_Demand : BOOL;
    B_DutyIsPump1 : BOOL;
    B_Pump1Available : BOOL;
    B_Pump2Available : BOOL;
    B_Pump1Feedback : BOOL;
    B_Pump2Feedback : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_GrantA : BOOL;
    A_GrantB : BOOL;
    A_Busy : BOOL;
    A_Turn : INT;
    A_LockedOut : BOOL;
    B_Pump1Run : BOOL;
    B_Pump2Run : BOOL;
    B_FailoverActive : BOOL;
    B_Failure : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
