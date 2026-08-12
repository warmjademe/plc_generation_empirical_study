FUNCTION_BLOCK C04_B03_composite
VAR_INPUT
    A_Event : BOOL;
    A_Qualify : BOOL;
    A_Reset : BOOL;
    A_MaxCount : INT;
    B_Button : BOOL;
    B_Enable : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Count : INT;
    A_AcceptedPulse : BOOL;
    A_AtLimit : BOOL;
    B_State : BOOL;
    B_AcceptedPulse : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
