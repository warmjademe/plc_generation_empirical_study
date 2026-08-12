FUNCTION_BLOCK C06_M02_bounded_up_down_counter
VAR_INPUT
    AddItem : BOOL;
    RemoveItem : BOOL;
    Reset : BOOL;
    Capacity : INT;
END_VAR
VAR_OUTPUT
    Count : INT;
    Empty : BOOL;
    Full : BOOL;
    Conflict : BOOL;
END_VAR
END_FUNCTION_BLOCK
