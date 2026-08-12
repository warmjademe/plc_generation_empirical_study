FUNCTION_BLOCK C08_B01_composite
VAR_INPUT
    A_Start : BOOL;
    A_Advance : BOOL;
    A_Pause : BOOL;
    A_Resume : BOOL;
    A_Abort : BOOL;
    A_Reset : BOOL;
    B_Start : BOOL;
    B_Sensor1 : BOOL;
    B_Sensor2 : BOOL;
    B_Stop : BOOL;
    B_ResetFault : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Step1 : BOOL;
    A_Step2 : BOOL;
    A_Paused : BOOL;
    A_Aborted : BOOL;
    A_State : INT;
    B_Actuator1 : BOOL;
    B_Actuator2 : BOOL;
    B_Complete : BOOL;
    B_Fault : BOOL;
    B_State : INT;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
