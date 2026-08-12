FUNCTION_BLOCK C08_B14_composite
VAR_INPUT
    A_Start : BOOL;
    A_HighLevel : BOOL;
    A_MixDone : BOOL;
    A_LowLevel : BOOL;
    A_Abort : BOOL;
    B_Start : BOOL;
    B_Sensor1 : BOOL;
    B_Sensor2 : BOOL;
    B_Stop : BOOL;
    B_ResetFault : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_FillValve : BOOL;
    A_Mixer : BOOL;
    A_DrainValve : BOOL;
    A_Complete : BOOL;
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
