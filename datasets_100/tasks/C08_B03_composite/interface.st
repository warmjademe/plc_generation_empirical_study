FUNCTION_BLOCK C08_B03_composite
VAR_INPUT
    A_Start : BOOL;
    A_Advance : BOOL;
    A_Pause : BOOL;
    A_Resume : BOOL;
    A_Abort : BOOL;
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
    A_Step1 : BOOL;
    A_Step2 : BOOL;
    A_Paused : BOOL;
    A_Aborted : BOOL;
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
