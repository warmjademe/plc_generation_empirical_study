FUNCTION_BLOCK C09_B18_composite
VAR_INPUT
    A_WarningCondition : BOOL;
    A_TripCondition : BOOL;
    A_Enable : BOOL;
    A_Shelve : BOOL;
    A_Acknowledge : BOOL;
    A_Reset : BOOL;
    B_WarningCondition : BOOL;
    B_TripCondition : BOOL;
    B_Enable : BOOL;
    B_Acknowledge : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Warning : BOOL;
    A_Trip : BOOL;
    A_Unacked : BOOL;
    A_Shelved : BOOL;
    A_LockedOut : BOOL;
    B_Warning : BOOL;
    B_Trip : BOOL;
    B_Unacked : BOOL;
    B_LockedOut : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_WarningDelay : TON;
    A_NewWarning : BOOL;
    B_WarningTimer : TON;
    B_PrevWarning : BOOL;
    B_PrevTrip : BOOL;
END_VAR

A_WarningDelay(IN := A_Enable AND A_WarningCondition AND (NOT A_Shelved) AND (NOT A_Trip), PT := T#300ms);
A_NewWarning := A_WarningDelay.Q AND (NOT A_Warning);
IF A_Enable AND A_TripCondition THEN
    A_Trip := FALSE;
    A_LockedOut := TRUE;
    A_Shelved := FALSE;
    A_Unacked := TRUE;
ELSE
    IF A_Shelve AND (NOT A_Trip) THEN A_Shelved := TRUE;
    ELSIF NOT A_Shelve THEN A_Shelved := FALSE;
    END_IF;
    IF A_NewWarning THEN A_Unacked := TRUE; END_IF;
END_IF;
A_Warning := A_WarningDelay.Q AND A_Enable AND (NOT A_Shelved) AND (NOT A_Trip);
IF A_Acknowledge THEN A_Unacked := FALSE; END_IF;
IF A_Reset AND (NOT A_Enable) AND (NOT A_WarningCondition) AND (NOT A_TripCondition) THEN
    A_Trip := FALSE;
    A_LockedOut := FALSE;
    A_Unacked := FALSE;
    A_Shelved := FALSE;
END_IF;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Warning THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

IF SubsystemBEnable AND CrossReady THEN
    B_WarningTimer(IN := B_Enable AND B_WarningCondition, PT := T#300ms);
    B_Warning := B_WarningTimer.Q;
    IF B_Enable AND B_TripCondition THEN
        B_Trip := TRUE;
        B_LockedOut := TRUE;
    END_IF;
    IF (B_Warning AND (NOT B_PrevWarning)) OR (B_Trip AND (NOT B_PrevTrip)) THEN
        B_Unacked := TRUE;
    END_IF;
    IF B_Acknowledge THEN
        B_Unacked := FALSE;
    END_IF;
    IF B_Reset AND (NOT B_Enable) AND (NOT B_WarningCondition) AND (NOT B_TripCondition) THEN
        B_Trip := FALSE;
        B_LockedOut := FALSE;
    END_IF;
    B_PrevWarning := B_Warning;
    B_PrevTrip := B_Trip;
ELSE
    B_Warning := FALSE;
    B_Trip := FALSE;
    B_Unacked := FALSE;
    B_LockedOut := FALSE;
END_IF;

END_FUNCTION_BLOCK
