FUNCTION_BLOCK C01_B08_composite
VAR_INPUT
    A_ChA : BOOL;
    A_ChB : BOOL;
    A_TestMode : BOOL;
    A_TestPermit : BOOL;
    A_ProcessRequest : BOOL;
    B_Ch1 : BOOL;
    B_Ch2 : BOOL;
    B_Ch3 : BOOL;
    B_AutoMode : BOOL;
    B_AutoRequest : BOOL;
    B_ManualRequest : BOOL;
    B_BypassRequest : BOOL;
    B_BypassPermit : BOOL;
    B_SafetyOK : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_SafeEnable : BOOL;
    A_Disagree : BOOL;
    A_TestActive : BOOL;
    B_RunPermit : BOOL;
    B_Degraded : BOOL;
    B_BypassActive : BOOL;
    B_Blocked : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
