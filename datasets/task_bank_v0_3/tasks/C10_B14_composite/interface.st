FUNCTION_BLOCK C10_B14_composite
VAR_INPUT
    A_LowDemand : BOOL;
    A_HighDemand : BOOL;
    A_LeadIsPump1 : BOOL;
    A_Pump1Available : BOOL;
    A_Pump2Available : BOOL;
    B_RequestA : BOOL;
    B_RequestB : BOOL;
    B_Done : BOOL;
    B_Emergency : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Pump1Run : BOOL;
    A_Pump2Run : BOOL;
    A_CapacityShortfall : BOOL;
    B_GrantA : BOOL;
    B_GrantB : BOOL;
    B_Busy : BOOL;
    B_Turn : INT;
    B_LockedOut : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
