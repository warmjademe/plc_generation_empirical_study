FUNCTION_BLOCK C09_H01_first_out_fault_recorder
VAR_INPUT
    FaultA : BOOL;
    FaultB : BOOL;
    FaultC : BOOL;
    Reset : BOOL;
END_VAR
VAR_OUTPUT
    AnyFault : BOOL;
    LockedOut : BOOL;
    FirstFault : INT;
END_VAR

AnyFault := FaultA OR FaultB OR FaultC;
IF (NOT LockedOut) AND AnyFault THEN
    LockedOut := TRUE;
    IF FaultA THEN
        FirstFault := 1;
    ELSIF FaultB THEN
        FirstFault := 2;
    ELSE
        FirstFault := 3;
    END_IF;
ELSIF Reset AND (NOT AnyFault) THEN
    LockedOut := FALSE;
    FirstFault := 0;
END_IF;

END_FUNCTION_BLOCK
