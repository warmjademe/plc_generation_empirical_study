FUNCTION_BLOCK C05_B19_composite
VAR_INPUT
    A_Start : BOOL;
    A_Stop : BOOL;
    A_Permit : BOOL;
    A_OilPressure : BOOL;
    A_MotorFeedback : BOOL;
    A_Reset : BOOL;
    B_Demand : BOOL;
    B_SafetyTrip : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_LubePump : BOOL;
    A_MotorCommand : BOOL;
    A_Cooldown : BOOL;
    A_Fault : BOOL;
    A_State : INT;
    B_Fan : BOOL;
    B_RunOn : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
