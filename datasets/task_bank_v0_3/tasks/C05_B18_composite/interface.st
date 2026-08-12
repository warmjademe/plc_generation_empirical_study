FUNCTION_BLOCK C05_B18_composite
VAR_INPUT
    A_Start : BOOL;
    A_Stop : BOOL;
    A_Permit : BOOL;
    A_OilPressure : BOOL;
    A_MotorFeedback : BOOL;
    A_Reset : BOOL;
    B_Start : BOOL;
    B_Stop : BOOL;
    B_Overload : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_LubePump : BOOL;
    A_MotorCommand : BOOL;
    A_Cooldown : BOOL;
    A_Fault : BOOL;
    A_State : INT;
    B_Main : BOOL;
    B_Star : BOOL;
    B_Delta : BOOL;
    B_Fault : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
