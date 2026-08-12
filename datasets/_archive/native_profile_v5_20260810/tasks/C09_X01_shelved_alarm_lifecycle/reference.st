FUNCTION_BLOCK C09_X01_shelved_alarm_lifecycle
VAR_INPUT
    WarningCondition : BOOL;
    TripCondition : BOOL;
    Enable : BOOL;
    Shelve : BOOL;
    Acknowledge : BOOL;
    Reset : BOOL;
END_VAR
VAR_OUTPUT
    Warning : BOOL;
    Trip : BOOL;
    Unacked : BOOL;
    Shelved : BOOL;
    LockedOut : BOOL;
END_VAR
VAR
    WarningDelay : TON;
    NewWarning : BOOL;
END_VAR

WarningDelay(IN := Enable AND WarningCondition AND (NOT Shelved) AND (NOT Trip), PT := T#300ms);
NewWarning := WarningDelay.Q AND (NOT Warning);
IF Enable AND TripCondition THEN
    Trip := TRUE;
    LockedOut := TRUE;
    Shelved := FALSE;
    Unacked := TRUE;
ELSE
    IF Shelve AND (NOT Trip) THEN Shelved := TRUE;
    ELSIF NOT Shelve THEN Shelved := FALSE;
    END_IF;
    IF NewWarning THEN Unacked := TRUE; END_IF;
END_IF;
Warning := WarningDelay.Q AND Enable AND (NOT Shelved) AND (NOT Trip);
IF Acknowledge THEN Unacked := FALSE; END_IF;
IF Reset AND (NOT Enable) AND (NOT WarningCondition) AND (NOT TripCondition) THEN
    Trip := FALSE;
    LockedOut := FALSE;
    Unacked := FALSE;
    Shelved := FALSE;
END_IF;

END_FUNCTION_BLOCK
