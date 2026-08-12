FUNCTION_BLOCK C06_B14_composite
VAR_INPUT
    A_AddItem : BOOL;
    A_RemoveItem : BOOL;
    A_Reset : BOOL;
    A_Capacity : INT;
    B_Inspected : BOOL;
    B_Rejected : BOOL;
    B_Reset : BOOL;
    B_WindowSize : INT;
    B_RejectLimit : INT;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Count : INT;
    A_Empty : BOOL;
    A_Full : BOOL;
    A_Conflict : BOOL;
    B_WindowCount : INT;
    B_RejectCount : INT;
    B_LockedOut : BOOL;
    B_WindowComplete : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
