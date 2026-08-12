FUNCTION_BLOCK C05_B03_composite
VAR_INPUT
    A_Start : BOOL;
    A_Stop : BOOL;
    A_Permit : BOOL;
    A_Stage1Feedback : BOOL;
    B_MonitorEnable : BOOL;
    B_Heartbeat : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Stage1 : BOOL;
    A_Stage2 : BOOL;
    A_Fault : BOOL;
    B_TimedOut : BOOL;
    B_Healthy : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
