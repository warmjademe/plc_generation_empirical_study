FUNCTION_BLOCK C09_B17_composite
VAR_INPUT
    A_WarningCondition : BOOL;
    A_TripCondition : BOOL;
    A_Enable : BOOL;
    A_Shelve : BOOL;
    A_Acknowledge : BOOL;
    A_Reset : BOOL;
    B_FaultA : BOOL;
    B_FaultB : BOOL;
    B_FaultC : BOOL;
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
    B_AnyFault : BOOL;
    B_LockedOut : BOOL;
    B_FirstFault : INT;
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
    B_AnyFault := B_FaultA OR B_FaultB OR B_FaultC;
    IF (NOT B_LockedOut) AND B_AnyFault THEN
        B_LockedOut := TRUE;
        IF B_FaultA THEN
            B_FirstFault := 1;
        ELSIF B_FaultB THEN
            B_FirstFault := 2;
        ELSE
            B_FirstFault := 3;
        END_IF;
    ELSIF B_Reset AND (NOT B_AnyFault) THEN
        B_LockedOut := FALSE;
        B_FirstFault := 0;
    END_IF;
ELSE
    B_AnyFault := FALSE;
    B_LockedOut := FALSE;
    B_FirstFault := 0;
END_IF;

END_FUNCTION_BLOCK
