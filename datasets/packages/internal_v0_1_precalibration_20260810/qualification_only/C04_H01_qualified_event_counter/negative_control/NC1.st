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
VAR
    PrevEvent : BOOL := FALSE;
END_VAR

AcceptedPulse := FALSE;
IF Reset THEN
    Count := 0;
ELSIF Event AND (NOT PrevEvent) AND Qualify AND (Count < Limit) THEN
    Count := Count + 1;
    AcceptedPulse := FALSE;
END_IF;
AtLimit := Count >= Limit;
PrevEvent := Event;

END_FUNCTION_BLOCK
