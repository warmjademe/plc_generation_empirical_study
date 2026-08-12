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
END_FUNCTION_BLOCK
