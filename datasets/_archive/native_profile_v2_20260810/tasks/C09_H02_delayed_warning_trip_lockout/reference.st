FUNCTION_BLOCK C09_H02_delayed_warning_trip_lockout
VAR_INPUT
    WarningCondition : BOOL;
    TripCondition : BOOL;
    Enable : BOOL;
    Acknowledge : BOOL;
    Reset : BOOL;
END_VAR
VAR_OUTPUT
    Warning : BOOL;
    Trip : BOOL;
    Unacked : BOOL;
    LockedOut : BOOL;
END_VAR
VAR
    WarningTimer : TON;
    PrevWarning : BOOL;
    PrevTrip : BOOL;
END_VAR

WarningTimer(IN := Enable AND WarningCondition, PT := T#300ms);
Warning := WarningTimer.Q;
IF Enable AND TripCondition THEN
    Trip := TRUE;
    LockedOut := TRUE;
END_IF;
IF (Warning AND (NOT PrevWarning)) OR (Trip AND (NOT PrevTrip)) THEN
    Unacked := TRUE;
END_IF;
IF Acknowledge THEN
    Unacked := FALSE;
END_IF;
IF Reset AND (NOT Enable) AND (NOT WarningCondition) AND (NOT TripCondition) THEN
    Trip := FALSE;
    LockedOut := FALSE;
END_IF;
PrevWarning := Warning;
PrevTrip := Trip;

END_FUNCTION_BLOCK
