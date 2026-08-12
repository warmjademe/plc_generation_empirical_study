FUNCTION_BLOCK C09_B03_composite
VAR_INPUT
    A_FaultA : BOOL;
    A_FaultB : BOOL;
    A_FaultC : BOOL;
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
    A_AnyFault : BOOL;
    A_LockedOut : BOOL;
    A_FirstFault : INT;
    B_Alarm : BOOL;
    B_Disagreeing : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    B_DisagreeTimer : TON;
END_VAR

A_AnyFault := A_FaultA OR A_FaultB OR A_FaultC;
IF (NOT A_LockedOut) AND A_AnyFault THEN
    A_LockedOut := FALSE;
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
