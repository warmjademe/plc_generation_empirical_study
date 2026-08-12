FUNCTION_BLOCK C09_B09_composite
VAR_INPUT
    A_Value : REAL;
    A_HighLimit : REAL;
    A_HighHighLimit : REAL;
    A_Reset : BOOL;
    B_FaultA : BOOL;
    B_FaultB : BOOL;
    B_FaultC : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_HighAlarm : BOOL;
    A_HighHighAlarm : BOOL;
    A_Shutdown : BOOL;
    B_AnyFault : BOOL;
    B_LockedOut : BOOL;
    B_FirstFault : INT;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR

IF A_Value >= A_HighHighLimit THEN
    A_HighAlarm := TRUE;
    A_HighHighAlarm := TRUE;
    A_Shutdown := TRUE;
ELSIF A_Value >= A_HighLimit THEN
    A_HighAlarm := TRUE;
END_IF;
IF A_Reset AND (A_Value < A_HighLimit) THEN
    A_HighAlarm := FALSE;
    A_HighHighAlarm := FALSE;
    A_Shutdown := FALSE;
END_IF;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_HighAlarm THEN
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
