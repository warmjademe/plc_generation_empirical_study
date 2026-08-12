FUNCTION_BLOCK C09_B13_composite
VAR_INPUT
    A_SensorA : REAL;
    A_SensorB : REAL;
    A_MaxDifference : REAL;
    A_Enable : BOOL;
    A_Reset : BOOL;
    B_FaultA : BOOL;
    B_FaultB : BOOL;
    B_FaultC : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Alarm : BOOL;
    A_Disagreeing : BOOL;
    B_AnyFault : BOOL;
    B_LockedOut : BOOL;
    B_FirstFault : INT;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_DisagreeTimer : TON;
END_VAR

A_Disagreeing := A_Enable AND (ABS(A_SensorA - A_SensorB) > A_MaxDifference);
A_DisagreeTimer(IN := A_Disagreeing, PT := T#300ms);
IF A_DisagreeTimer.Q THEN
    A_Alarm := FALSE;
ELSIF A_Reset AND (NOT A_Disagreeing) THEN
    A_Alarm := FALSE;
END_IF;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Alarm THEN
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
