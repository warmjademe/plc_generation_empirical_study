FUNCTION_BLOCK C08_B11_composite
VAR_INPUT
    A_ItemPresent : BOOL;
    A_RejectClass : BOOL;
    A_TransferDone : BOOL;
    A_Reset : BOOL;
    B_Start : BOOL;
    B_HighLevel : BOOL;
    B_MixDone : BOOL;
    B_LowLevel : BOOL;
    B_Abort : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Inspect : BOOL;
    A_AcceptGate : BOOL;
    A_RejectGate : BOOL;
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
