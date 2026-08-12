FUNCTION_BLOCK C09_B19_composite
VAR_INPUT
    A_WarningCondition : BOOL;
    A_TripCondition : BOOL;
    A_Enable : BOOL;
    A_Shelve : BOOL;
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
    A_Shelved : BOOL;
    A_LockedOut : BOOL;
    B_HighAlarm : BOOL;
    B_HighHighAlarm : BOOL;
    B_Shutdown : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_WarningDelay : TON;
    A_NewWarning : BOOL;
END_VAR

A_WarningDelay(IN := A_Enable AND A_WarningCondition AND (NOT A_Shelved) AND (NOT A_Trip), PT := T#300ms);
A_NewWarning := A_WarningDelay.Q AND (NOT A_Warning);
IF A_Enable AND A_TripCondition THEN
    A_Trip := TRUE;
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
