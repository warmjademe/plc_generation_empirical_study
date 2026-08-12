FUNCTION_BLOCK C06_X01_batch_quality_lockout
VAR_INPUT
    ItemPulse : BOOL;
    Rejected : BOOL;
    Stop : BOOL;
    Reset : BOOL;
    Target : INT;
    RejectLimit : INT;
END_VAR
VAR_OUTPUT
    AcceptedCount : INT;
    RejectCount : INT;
    ConsecutiveRejects : INT;
    Complete : BOOL;
    LockedOut : BOOL;
END_VAR
END_FUNCTION_BLOCK
