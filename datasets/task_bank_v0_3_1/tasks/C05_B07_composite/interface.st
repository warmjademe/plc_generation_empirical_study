FUNCTION_BLOCK C05_B07_composite
VAR_INPUT
    A_Start : BOOL;
    A_Stop : BOOL;
    A_Overload : BOOL;
    A_Reset : BOOL;
    B_MonitorEnable : BOOL;
    B_Heartbeat : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Main : BOOL;
    A_Star : BOOL;
    A_Delta : BOOL;
    A_Fault : BOOL;
    B_TimedOut : BOOL;
    B_Healthy : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
