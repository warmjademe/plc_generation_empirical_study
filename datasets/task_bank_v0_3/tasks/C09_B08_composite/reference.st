FUNCTION_BLOCK C09_B08_composite
VAR_INPUT
    A_WarningCondition : BOOL;
    A_TripCondition : BOOL;
    A_Enable : BOOL;
    A_Acknowledge : BOOL;
    A_Reset : BOOL;
    B_WarningCondition : BOOL;
    B_TripCondition : BOOL;
    B_Enable : BOOL;
    B_Shelve : BOOL;
    B_Acknowledge : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Warning : BOOL;
    A_Trip : BOOL;
    A_Unacked : BOOL;
    A_LockedOut : BOOL;
    B_Warning : BOOL;
    B_Trip : BOOL;
    B_Unacked : BOOL;
    B_Shelved : BOOL;
    B_LockedOut : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_WarningTimer : TON;
    A_PrevWarning : BOOL;
    A_PrevTrip : BOOL;
    B_WarningDelay : TON;
    B_NewWarning : BOOL;
END_VAR

A_WarningTimer(IN := A_Enable AND A_WarningCondition, PT := T#300ms);
A_Warning := A_WarningTimer.Q;
IF A_Enable AND A_TripCondition THEN
    A_Trip := TRUE;
    A_LockedOut := TRUE;
END_IF;
IF (A_Warning AND (NOT A_PrevWarning)) OR (A_Trip AND (NOT A_PrevTrip)) THEN
    A_Unacked := TRUE;
END_IF;
IF A_Acknowledge THEN
    A_Unacked := FALSE;
END_IF;
IF A_Reset AND (NOT A_Enable) AND (NOT A_WarningCondition) AND (NOT A_TripCondition) THEN
    A_Trip := FALSE;
    A_LockedOut := FALSE;
END_IF;
A_PrevWarning := A_Warning;
A_PrevTrip := A_Trip;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Warning THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

IF SubsystemBEnable AND CrossReady THEN
    B_WarningDelay(IN := B_Enable AND B_WarningCondition AND (NOT B_Shelved) AND (NOT B_Trip), PT := T#300ms);
    B_NewWarning := B_WarningDelay.Q AND (NOT B_Warning);
    IF B_Enable AND B_TripCondition THEN
        B_Trip := TRUE;
        B_LockedOut := TRUE;
        B_Shelved := FALSE;
        B_Unacked := TRUE;
    ELSE
        IF B_Shelve AND (NOT B_Trip) THEN B_Shelved := TRUE;
        ELSIF NOT B_Shelve THEN B_Shelved := FALSE;
        END_IF;
        IF B_NewWarning THEN B_Unacked := TRUE; END_IF;
    END_IF;
    B_Warning := B_WarningDelay.Q AND B_Enable AND (NOT B_Shelved) AND (NOT B_Trip);
    IF B_Acknowledge THEN B_Unacked := FALSE; END_IF;
    IF B_Reset AND (NOT B_Enable) AND (NOT B_WarningCondition) AND (NOT B_TripCondition) THEN
        B_Trip := FALSE;
        B_LockedOut := FALSE;
        B_Unacked := FALSE;
        B_Shelved := FALSE;
    END_IF;
ELSE
    B_Warning := FALSE;
    B_Trip := FALSE;
    B_Unacked := FALSE;
    B_Shelved := FALSE;
    B_LockedOut := FALSE;
END_IF;

END_FUNCTION_BLOCK
