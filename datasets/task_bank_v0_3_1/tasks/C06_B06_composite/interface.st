FUNCTION_BLOCK C06_B06_composite
VAR_INPUT
    A_Inspected : BOOL;
    A_Rejected : BOOL;
    A_Reset : BOOL;
    A_WindowSize : INT;
    A_RejectLimit : INT;
    B_Item : BOOL;
    B_Reset : BOOL;
    B_Target : INT;
    B_Enable : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_WindowCount : INT;
    A_RejectCount : INT;
    A_LockedOut : BOOL;
    A_WindowComplete : BOOL;
    B_Count : INT;
    B_BatchDone : BOOL;
    B_Accepted : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
