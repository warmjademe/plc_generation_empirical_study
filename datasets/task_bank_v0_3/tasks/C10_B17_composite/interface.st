FUNCTION_BLOCK C10_B17_composite
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
    A_Run1 : BOOL;
    A_Run2 : BOOL;
    A_Run3 : BOOL;
    A_ActiveCount : INT;
    A_Failover : BOOL;
    A_Fault : BOOL;
    B_Pump1Run : BOOL;
    B_Pump2Run : BOOL;
    B_FailoverActive : BOOL;
    B_Failure : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
