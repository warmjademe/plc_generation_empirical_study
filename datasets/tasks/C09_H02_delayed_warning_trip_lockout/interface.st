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
END_FUNCTION_BLOCK
