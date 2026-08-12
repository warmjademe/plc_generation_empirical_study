FUNCTION_BLOCK C04_H01_qualified_event_counter
VAR_INPUT
    Event : BOOL;
    Qualify : BOOL;
    Reset : BOOL;
    Limit : INT;
END_VAR
VAR_OUTPUT
    Count : INT;
    AcceptedPulse : BOOL;
    AtLimit : BOOL;
END_VAR
END_FUNCTION_BLOCK
