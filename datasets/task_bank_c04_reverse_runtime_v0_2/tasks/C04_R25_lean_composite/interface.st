FUNCTION_BLOCK C04_R25_lean_composite
VAR_INPUT
    A_Ch1 : BOOL;
    A_Ch2 : BOOL;
    A_Ch3 : BOOL;
    A_AutoMode : BOOL;
    A_AutoRequest : BOOL;
    A_ManualRequest : BOOL;
    A_BypassRequest : BOOL;
    A_BypassPermit : BOOL;
    A_SafetyOK : BOOL;
    A_Reset : BOOL;
    B_EventA : BOOL;
    B_EventB : BOOL;
    B_Qualify : BOOL;
    B_Inhibit : BOOL;
    B_Reset : BOOL;
    B_MaxCount : INT;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_RunPermit : BOOL;
    A_Degraded : BOOL;
    A_BypassActive : BOOL;
    A_Blocked : BOOL;
    B_PulseA : BOOL;
    B_PulseB : BOOL;
    B_Count : INT;
    B_Locked : BOOL;
    B_LastSource : INT;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
