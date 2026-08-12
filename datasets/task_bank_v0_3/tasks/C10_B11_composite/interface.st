FUNCTION_BLOCK C10_B11_composite
VAR_INPUT
    A_Demand : BOOL;
    A_Pump1Available : BOOL;
    A_Pump2Available : BOOL;
    A_Reset : BOOL;
    B_LowDemand : BOOL;
    B_HighDemand : BOOL;
    B_LeadIsPump1 : BOOL;
    B_Pump1Available : BOOL;
    B_Pump2Available : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Pump1Run : BOOL;
    A_Pump2Run : BOOL;
    A_NextPump : INT;
    A_Unavailable : BOOL;
    B_Pump1Run : BOOL;
    B_Pump2Run : BOOL;
    B_CapacityShortfall : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
