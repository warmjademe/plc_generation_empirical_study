FUNCTION_BLOCK C06_M01_configurable_batch_counter
VAR_INPUT
    Item : BOOL;
    Reset : BOOL;
    Target : INT;
    Enable : BOOL;
END_VAR
VAR_OUTPUT
    Count : INT;
    BatchDone : BOOL;
    Accepted : BOOL;
END_VAR
VAR
    PrevItem : BOOL := FALSE;
END_VAR

Accepted := FALSE;
IF Reset THEN
    Count := 0;
ELSIF Enable AND Item AND (NOT PrevItem) AND (Count < Target) THEN
    Count := Count + 1;
    Accepted := TRUE;
END_IF;
BatchDone := Count >= Target;
PrevItem := Item;

END_FUNCTION_BLOCK
