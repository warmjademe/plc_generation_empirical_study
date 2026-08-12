FUNCTION_BLOCK C09_B14_composite
VAR_INPUT
    A_SensorA : REAL;
    A_SensorB : REAL;
    A_MaxDifference : REAL;
    A_Enable : BOOL;
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
    A_Alarm : BOOL;
    A_Disagreeing : BOOL;
    B_Warning : BOOL;
    B_Trip : BOOL;
    B_Unacked : BOOL;
    B_LockedOut : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_DisagreeTimer : TON;
    B_WarningTimer : TON;
    B_PrevWarning : BOOL;
    B_PrevTrip : BOOL;
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
