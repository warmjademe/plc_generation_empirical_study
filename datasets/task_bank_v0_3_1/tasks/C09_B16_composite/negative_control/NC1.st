FUNCTION_BLOCK C09_B16_composite
VAR_INPUT
    A_SensorA : REAL;
    A_SensorB : REAL;
    A_MaxDifference : REAL;
    A_Enable : BOOL;
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
    A_Alarm : BOOL;
    A_Disagreeing : BOOL;
    B_Warning : BOOL;
    B_Trip : BOOL;
    B_Unacked : BOOL;
    B_Shelved : BOOL;
    B_LockedOut : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_DisagreeTimer : TON;
    B_WarningDelay : TON;
    B_NewWarning : BOOL;
END_VAR

A_Disagreeing := A_Enable AND (ABS(A_SensorA - A_SensorB) > A_MaxDifference);
A_DisagreeTimer(IN := A_Disagreeing, PT := T#300ms);
IF A_DisagreeTimer.Q THEN
    A_Alarm := TRUE;
ELSIF A_Reset AND (NOT A_Disagreeing) THEN
    A_Alarm := FALSE;
END_IF;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Alarm THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := FALSE;

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
