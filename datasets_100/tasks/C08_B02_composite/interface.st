FUNCTION_BLOCK C08_B02_composite
VAR_INPUT
    A_Start : BOOL;
    A_Advance : BOOL;
    A_Pause : BOOL;
    A_Resume : BOOL;
    A_Abort : BOOL;
    A_Reset : BOOL;
    B_ItemPresent : BOOL;
    B_RejectClass : BOOL;
    B_TransferDone : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Step1 : BOOL;
    A_Step2 : BOOL;
    A_Paused : BOOL;
    A_Aborted : BOOL;
    A_State : INT;
    B_Inspect : BOOL;
    B_AcceptGate : BOOL;
    B_RejectGate : BOOL;
    B_State : INT;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
