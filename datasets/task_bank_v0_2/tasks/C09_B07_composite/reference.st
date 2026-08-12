FUNCTION_BLOCK C09_B07_composite
VAR_INPUT
    A_WarningCondition : BOOL;
    A_TripCondition : BOOL;
    A_Enable : BOOL;
    A_Acknowledge : BOOL;
    A_Reset : BOOL;
    B_SensorA : REAL;
    B_SensorB : REAL;
    B_MaxDifference : REAL;
    B_Enable : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Warning : BOOL;
    A_Trip : BOOL;
    A_Unacked : BOOL;
    A_LockedOut : BOOL;
    B_Alarm : BOOL;
    B_Disagreeing : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_WarningTimer : TON;
    A_PrevWarning : BOOL;
    A_PrevTrip : BOOL;
    B_DisagreeTimer : TON;
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
    B_Disagreeing := B_Enable AND (ABS(B_SensorA - B_SensorB) > B_MaxDifference);
    B_DisagreeTimer(IN := B_Disagreeing, PT := T#300ms);
    IF B_DisagreeTimer.Q THEN
        B_Alarm := TRUE;
    ELSIF B_Reset AND (NOT B_Disagreeing) THEN
        B_Alarm := FALSE;
    END_IF;
ELSE
    B_Alarm := FALSE;
    B_Disagreeing := FALSE;
END_IF;

END_FUNCTION_BLOCK
