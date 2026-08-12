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
VAR
    PrevItem : BOOL;
END_VAR

IF Reset AND Stop AND (NOT ItemPulse) THEN
    AcceptedCount := 0;
    RejectCount := 0;
    ConsecutiveRejects := 0;
    Complete := FALSE;
    LockedOut := FALSE;
ELSIF RejectLimit <= 0 THEN
    LockedOut := TRUE;
ELSIF ItemPulse AND (NOT PrevItem) AND (NOT Stop) AND (NOT Complete) AND (NOT LockedOut) THEN
    IF Rejected THEN
        RejectCount := RejectCount + 1;
        ConsecutiveRejects := ConsecutiveRejects + 1;
        IF ConsecutiveRejects >= RejectLimit THEN LockedOut := TRUE; END_IF;
    ELSE
        AcceptedCount := AcceptedCount + 1;
        ConsecutiveRejects := 0;
        IF (Target > 0) AND (AcceptedCount >= Target) THEN Complete := TRUE; END_IF;
    END_IF;
END_IF;
PrevItem := ItemPulse;

END_FUNCTION_BLOCK
