FUNCTION_BLOCK C09_B01_composite
VAR_INPUT
    A_FaultA : BOOL;
    A_FaultB : BOOL;
    A_FaultC : BOOL;
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
    A_AnyFault : BOOL;
    A_LockedOut : BOOL;
    A_FirstFault : INT;
    B_Warning : BOOL;
    B_Trip : BOOL;
    B_Unacked : BOOL;
    B_LockedOut : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    B_WarningTimer : TON;
    B_PrevWarning : BOOL;
    B_PrevTrip : BOOL;
END_VAR

A_AnyFault := A_FaultA OR A_FaultB OR A_FaultC;
IF (NOT A_LockedOut) AND A_AnyFault THEN
    A_LockedOut := TRUE;
    IF A_FaultA THEN
        A_FirstFault := 1;
    ELSIF A_FaultB THEN
        A_FirstFault := 2;
    ELSE
        A_FirstFault := 3;
    END_IF;
ELSIF A_Reset AND (NOT A_AnyFault) THEN
    A_LockedOut := FALSE;
    A_FirstFault := 0;
END_IF;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_AnyFault THEN
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
