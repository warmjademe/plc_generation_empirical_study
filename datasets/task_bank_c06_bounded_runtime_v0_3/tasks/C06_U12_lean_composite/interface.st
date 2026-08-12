FUNCTION_BLOCK C06_U12_lean_composite
VAR_INPUT
    A_Item : BOOL;
    A_Reset : BOOL;
    A_Target : INT;
    A_Enable : BOOL;
    B_ChA : BOOL;
    B_ChB : BOOL;
    B_TestMode : BOOL;
    B_TestPermit : BOOL;
    B_ProcessRequest : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Count : INT;
    A_BatchDone : BOOL;
    A_Accepted : BOOL;
    B_SafeEnable : BOOL;
    B_Disagree : BOOL;
    B_TestActive : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
