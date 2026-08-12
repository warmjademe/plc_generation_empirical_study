FUNCTION_BLOCK C05_B12_composite
VAR_INPUT
    A_Demand : BOOL;
    A_SafetyTrip : BOOL;
    B_Start : BOOL;
    B_Stop : BOOL;
    B_Permit : BOOL;
    B_OilPressure : BOOL;
    B_MotorFeedback : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Fan : BOOL;
    A_RunOn : BOOL;
    B_LubePump : BOOL;
    B_MotorCommand : BOOL;
    B_Cooldown : BOOL;
    B_Fault : BOOL;
    B_State : INT;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
