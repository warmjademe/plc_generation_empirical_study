FUNCTION_BLOCK C04_R22_lean_composite
VAR_INPUT
    A_EventA : BOOL;
    A_EventB : BOOL;
    A_Qualify : BOOL;
    A_Inhibit : BOOL;
    A_Reset : BOOL;
    A_MaxCount : INT;
    B_ChA : BOOL;
    B_ChB : BOOL;
    B_TestMode : BOOL;
    B_TestPermit : BOOL;
    B_ProcessRequest : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_PulseA : BOOL;
    A_PulseB : BOOL;
    A_Count : INT;
    A_Locked : BOOL;
    A_LastSource : INT;
    B_SafeEnable : BOOL;
    B_Disagree : BOOL;
    B_TestActive : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
