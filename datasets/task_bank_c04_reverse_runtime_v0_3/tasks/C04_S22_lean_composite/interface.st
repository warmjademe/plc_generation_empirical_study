FUNCTION_BLOCK C04_S22_lean_composite
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
    B_Arm : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_RunPermit : BOOL;
    A_Degraded : BOOL;
    A_BypassActive : BOOL;
    A_Blocked : BOOL;
    B_Captured : BOOL;
    B_Code : INT;
    B_Pulse : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
