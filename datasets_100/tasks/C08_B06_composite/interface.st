FUNCTION_BLOCK C08_B06_composite
VAR_INPUT
    A_Start : BOOL;
    A_Sensor1 : BOOL;
    A_Sensor2 : BOOL;
    A_Stop : BOOL;
    A_ResetFault : BOOL;
    B_ItemPresent : BOOL;
    B_RejectClass : BOOL;
    B_TransferDone : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Actuator1 : BOOL;
    A_Actuator2 : BOOL;
    A_Complete : BOOL;
    A_Fault : BOOL;
    A_State : INT;
    B_Inspect : BOOL;
    B_AcceptGate : BOOL;
    B_RejectGate : BOOL;
    B_State : INT;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
