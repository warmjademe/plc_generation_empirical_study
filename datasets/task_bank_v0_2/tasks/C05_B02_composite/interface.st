FUNCTION_BLOCK C05_B02_composite
VAR_INPUT
    A_Start : BOOL;
    A_Stop : BOOL;
    A_Permit : BOOL;
    A_Stage1Feedback : BOOL;
    B_Demand : BOOL;
    B_SafetyTrip : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Stage1 : BOOL;
    A_Stage2 : BOOL;
    A_Fault : BOOL;
    B_Fan : BOOL;
    B_RunOn : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
