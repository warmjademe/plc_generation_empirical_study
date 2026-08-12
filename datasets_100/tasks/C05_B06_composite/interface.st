FUNCTION_BLOCK C05_B06_composite
VAR_INPUT
    A_Start : BOOL;
    A_Stop : BOOL;
    A_Overload : BOOL;
    A_Reset : BOOL;
    B_Demand : BOOL;
    B_SafetyTrip : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Main : BOOL;
    A_Star : BOOL;
    A_Delta : BOOL;
    A_Fault : BOOL;
    B_Fan : BOOL;
    B_RunOn : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
