FUNCTION_BLOCK C05_B15_composite
VAR_INPUT
    A_MonitorEnable : BOOL;
    A_Heartbeat : BOOL;
    A_Reset : BOOL;
    B_Demand : BOOL;
    B_SafetyTrip : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_TimedOut : BOOL;
    A_Healthy : BOOL;
    B_Fan : BOOL;
    B_RunOn : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
