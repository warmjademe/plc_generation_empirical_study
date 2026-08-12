FUNCTION_BLOCK C04_S10_lean_composite
VAR_INPUT
    A_ChA : BOOL;
    A_ChB : BOOL;
    A_TestMode : BOOL;
    A_TestPermit : BOOL;
    A_ProcessRequest : BOOL;
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
    A_SafeEnable : BOOL;
    A_Disagree : BOOL;
    A_TestActive : BOOL;
    B_PulseA : BOOL;
    B_PulseB : BOOL;
    B_Count : INT;
    B_Locked : BOOL;
    B_LastSource : INT;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
