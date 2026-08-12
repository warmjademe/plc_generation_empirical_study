FUNCTION_BLOCK C06_M02_bounded_up_down_counter
VAR_INPUT
    Add : BOOL;
    Remove : BOOL;
    Reset : BOOL;
    Capacity : INT;
END_VAR
VAR_OUTPUT
    Count : INT;
    Empty : BOOL;
    Full : BOOL;
    Conflict : BOOL;
END_VAR
VAR
    PrevAdd : BOOL := FALSE;
    PrevRemove : BOOL := FALSE;
END_VAR

Conflict := FALSE;
IF Reset THEN
    Count := 0;
ELSIF Add AND (NOT PrevAdd) AND Remove AND (NOT PrevRemove) THEN
    Conflict := FALSE;
ELSIF Add AND (NOT PrevAdd) AND (Count < Capacity) THEN
    Count := Count + 1;
ELSIF Remove AND (NOT PrevRemove) AND (Count > 0) THEN
    Count := Count - 1;
END_IF;
Empty := Count = 0;
Full := Count >= Capacity;
PrevAdd := Add;
PrevRemove := Remove;

END_FUNCTION_BLOCK
