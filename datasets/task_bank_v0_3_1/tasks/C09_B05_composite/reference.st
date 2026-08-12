FUNCTION_BLOCK C09_B05_composite
VAR_INPUT
    A_WarningCondition : BOOL;
    A_TripCondition : BOOL;
    A_Enable : BOOL;
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
    A_LockedOut : BOOL;
    B_AnyFault : BOOL;
    B_LockedOut : BOOL;
    B_FirstFault : INT;
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
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

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
