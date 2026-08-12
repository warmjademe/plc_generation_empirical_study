FUNCTION_BLOCK C06_V05_lean_composite
VAR_INPUT
    A_Info : BOOL;
    A_Warning : BOOL;
    A_Trip : BOOL;
    A_Emergency : BOOL;
    A_Suppress : BOOL;
    B_ItemPulse : BOOL;
    B_Rejected : BOOL;
    B_Stop : BOOL;
    B_Reset : BOOL;
    B_Target : INT;
    B_RejectLimit : INT;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Active : BOOL;
    A_Level : INT;
    B_AcceptedCount : INT;
    B_RejectCount : INT;
    B_ConsecutiveRejects : INT;
    B_Complete : BOOL;
    B_LockedOut : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
