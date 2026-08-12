FUNCTION_BLOCK C10_B18_composite
VAR_INPUT
    A_LowDemand : BOOL;
    A_HighDemand : BOOL;
    A_Lead : INT;
    A_Available1 : BOOL;
    A_Available2 : BOOL;
    A_Available3 : BOOL;
    A_Feedback1 : BOOL;
    A_Feedback2 : BOOL;
    A_Feedback3 : BOOL;
    A_Stop : BOOL;
    A_Reset : BOOL;
    B_RequestA : BOOL;
    B_RequestB : BOOL;
    B_Done : BOOL;
    B_Emergency : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Run1 : BOOL;
    A_Run2 : BOOL;
    A_Run3 : BOOL;
    A_ActiveCount : INT;
    A_Failover : BOOL;
    A_Fault : BOOL;
    B_GrantA : BOOL;
    B_GrantB : BOOL;
    B_Busy : BOOL;
    B_Turn : INT;
    B_LockedOut : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
