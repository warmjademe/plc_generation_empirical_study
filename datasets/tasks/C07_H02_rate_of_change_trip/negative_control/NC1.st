FUNCTION_BLOCK C07_H02_rate_of_change_trip
VAR_INPUT
    Value : REAL;
    Enable : BOOL;
    MaxRise : REAL;
    MaxFall : REAL;
    Reset : BOOL;
END_VAR
VAR_OUTPUT
    Delta : REAL;
    Trip : BOOL;
    Ready : BOOL;
END_VAR
VAR
    Previous : REAL := 0.0;
END_VAR

IF NOT Enable THEN
    Ready := FALSE;
    Delta := 0.0;
    IF Reset THEN
        Trip := FALSE;
    END_IF;
ELSE
    IF NOT Ready THEN
        Previous := Value;
        Delta := 0.0;
        Ready := FALSE;
    ELSE
        Delta := Value - Previous;
        Previous := Value;
        IF (Delta > MaxRise) OR (Delta < (0.0 - MaxFall)) THEN
            Trip := TRUE;
        END_IF;
    END_IF;
END_IF;

END_FUNCTION_BLOCK
