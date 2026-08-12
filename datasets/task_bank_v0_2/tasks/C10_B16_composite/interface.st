FUNCTION_BLOCK C10_B16_composite
VAR_INPUT
    A_LowDemand : BOOL;
    A_HighDemand : BOOL;
    A_LeadIsPump1 : BOOL;
    A_Pump1Available : BOOL;
    A_Pump2Available : BOOL;
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
    A_Pump1Run : BOOL;
    A_Pump2Run : BOOL;
    A_CapacityShortfall : BOOL;
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
