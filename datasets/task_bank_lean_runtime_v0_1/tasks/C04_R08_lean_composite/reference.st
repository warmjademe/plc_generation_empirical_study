FUNCTION_BLOCK C04_R08_lean_composite
VAR_INPUT
    A_EventA : BOOL;
    A_EventB : BOOL;
    A_Arm : BOOL;
    A_Reset : BOOL;
    B_S1 : BOOL;
    B_S2 : BOOL;
    B_S3 : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Captured : BOOL;
    A_Code : INT;
    A_Pulse : BOOL;
    B_Vote : BOOL;
    B_Unanimous : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PrevA : BOOL := FALSE;
    A_PrevB : BOOL := FALSE;
END_VAR

A_Pulse := FALSE;
IF A_Reset THEN
    A_Captured := FALSE;
    A_Code := 0;
ELSIF A_Arm AND (NOT A_Captured) THEN
    IF A_EventA AND (NOT A_PrevA) THEN
        A_Captured := TRUE;
        A_Code := 1;
        A_Pulse := TRUE;
    ELSIF A_EventB AND (NOT A_PrevB) THEN
        A_Captured := TRUE;
        A_Code := 2;
        A_Pulse := TRUE;
    END_IF;
END_IF;
A_PrevA := A_EventA;
A_PrevB := A_EventB;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Captured THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

IF SubsystemBEnable AND CrossReady THEN
    B_Vote := (B_S1 AND B_S2) OR (B_S1 AND B_S3) OR (B_S2 AND B_S3);
    B_Unanimous := (B_S1 AND B_S2 AND B_S3) OR ((NOT B_S1) AND (NOT B_S2) AND (NOT B_S3));
ELSE
    B_Vote := FALSE;
    B_Unanimous := FALSE;
END_IF;

END_FUNCTION_BLOCK
