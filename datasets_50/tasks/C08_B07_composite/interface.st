FUNCTION_BLOCK C08_B07_composite
VAR_INPUT
    A_Start : BOOL;
    A_Sensor1 : BOOL;
    A_Sensor2 : BOOL;
    A_Stop : BOOL;
    A_ResetFault : BOOL;
    B_Start : BOOL;
    B_HighLevel : BOOL;
    B_MixDone : BOOL;
    B_LowLevel : BOOL;
    B_Abort : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Actuator1 : BOOL;
    A_Actuator2 : BOOL;
    A_Complete : BOOL;
    A_Fault : BOOL;
    A_State : INT;
    B_FillValve : BOOL;
    B_Mixer : BOOL;
    B_DrainValve : BOOL;
    B_Complete : BOOL;
    B_State : INT;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
