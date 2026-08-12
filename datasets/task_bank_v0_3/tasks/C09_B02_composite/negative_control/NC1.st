FUNCTION_BLOCK C09_B02_composite
VAR_INPUT
    A_FaultA : BOOL;
    A_FaultB : BOOL;
    A_FaultC : BOOL;
    A_Reset : BOOL;
    B_Value : REAL;
    B_HighLimit : REAL;
    B_HighHighLimit : REAL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_AnyFault : BOOL;
    A_LockedOut : BOOL;
    A_FirstFault : INT;
    B_HighAlarm : BOOL;
    B_HighHighAlarm : BOOL;
    B_Shutdown : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
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
