FUNCTION_BLOCK C04_B05_composite
VAR_INPUT
    A_EventA : BOOL;
    A_EventB : BOOL;
    A_Arm : BOOL;
    A_Reset : BOOL;
    B_Event : BOOL;
    B_Qualify : BOOL;
    B_Reset : BOOL;
    B_MaxCount : INT;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Captured : BOOL;
    A_Code : INT;
    A_Pulse : BOOL;
    B_Count : INT;
    B_AcceptedPulse : BOOL;
    B_AtLimit : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
