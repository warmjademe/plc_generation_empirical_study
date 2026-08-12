FUNCTION_BLOCK C08_B17_composite
VAR_INPUT
    A_Start : BOOL;
    A_Stage1Done : BOOL;
    A_Stage2Done : BOOL;
    A_Stage3Done : BOOL;
    A_Pause : BOOL;
    A_Abort : BOOL;
    A_Reset : BOOL;
    B_Start : BOOL;
    B_Advance : BOOL;
    B_Pause : BOOL;
    B_Resume : BOOL;
    B_Abort : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Actuator1 : BOOL;
    A_Actuator2 : BOOL;
    A_Actuator3 : BOOL;
    A_Paused : BOOL;
    A_Complete : BOOL;
    A_Fault : BOOL;
    A_State : INT;
    B_Step1 : BOOL;
    B_Step2 : BOOL;
    B_Paused : BOOL;
    B_Aborted : BOOL;
    B_State : INT;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
