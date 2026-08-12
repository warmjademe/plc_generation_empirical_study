FUNCTION_BLOCK C10_B08_composite
VAR_INPUT
    A_RequestA : BOOL;
    A_RequestB : BOOL;
    A_Done : BOOL;
    A_Emergency : BOOL;
    A_Reset : BOOL;
    B_LowDemand : BOOL;
    B_HighDemand : BOOL;
    B_Lead : INT;
    B_Available1 : BOOL;
    B_Available2 : BOOL;
    B_Available3 : BOOL;
    B_Feedback1 : BOOL;
    B_Feedback2 : BOOL;
    B_Feedback3 : BOOL;
    B_Stop : BOOL;
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
    B_Run1 : BOOL;
    B_Run2 : BOOL;
    B_Run3 : BOOL;
    B_ActiveCount : INT;
    B_Failover : BOOL;
    B_Fault : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
