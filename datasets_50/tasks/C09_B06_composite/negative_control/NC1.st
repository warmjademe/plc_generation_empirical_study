FUNCTION_BLOCK C09_B06_composite
VAR_INPUT
    A_WarningCondition : BOOL;
    A_TripCondition : BOOL;
    A_Enable : BOOL;
    A_Acknowledge : BOOL;
    A_Reset : BOOL;
    B_Value : REAL;
    B_HighLimit : REAL;
    B_HighHighLimit : REAL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Warning : BOOL;
    A_Trip : BOOL;
    A_Unacked : BOOL;
    A_LockedOut : BOOL;
    B_HighAlarm : BOOL;
    B_HighHighAlarm : BOOL;
    B_Shutdown : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_WarningTimer : TON;
    A_PrevWarning : BOOL;
    A_PrevTrip : BOOL;
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
CrossBlocked := FALSE;

IF SubsystemBEnable AND CrossReady THEN
    IF B_Value >= B_HighHighLimit THEN
        B_HighAlarm := TRUE;
        B_HighHighAlarm := TRUE;
        B_Shutdown := TRUE;
    ELSIF B_Value >= B_HighLimit THEN
        B_HighAlarm := TRUE;
    END_IF;
    IF B_Reset AND (B_Value < B_HighLimit) THEN
        B_HighAlarm := FALSE;
        B_HighHighAlarm := FALSE;
        B_Shutdown := FALSE;
    END_IF;
ELSE
    B_HighAlarm := FALSE;
    B_HighHighAlarm := FALSE;
    B_Shutdown := FALSE;
END_IF;

END_FUNCTION_BLOCK
