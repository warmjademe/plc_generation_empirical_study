FUNCTION_BLOCK C06_U14_lean_composite
VAR_INPUT
    A_Item : BOOL;
    A_Reset : BOOL;
    A_Target : INT;
    A_Enable : BOOL;
    B_AutoMode : BOOL;
    B_AutoDemand : BOOL;
    B_ManualDemand : BOOL;
    B_SafetyOK : BOOL;
    B_Inhibit : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Count : INT;
    A_BatchDone : BOOL;
    A_Accepted : BOOL;
    B_Command : BOOL;
    B_Blocked : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
