FUNCTION_BLOCK C05_B09_composite
VAR_INPUT
    A_Demand : BOOL;
    A_SafetyTrip : BOOL;
    B_Start : BOOL;
    B_Stop : BOOL;
    B_Permit : BOOL;
    B_Stage1Feedback : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Fan : BOOL;
    A_RunOn : BOOL;
    B_Stage1 : BOOL;
    B_Stage2 : BOOL;
    B_Fault : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
