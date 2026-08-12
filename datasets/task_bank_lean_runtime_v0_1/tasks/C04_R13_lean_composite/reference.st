FUNCTION_BLOCK C04_R13_lean_composite
VAR_INPUT
    A_Signal : BOOL;
    A_Arm : BOOL;
    B_S1 : BOOL;
    B_S2 : BOOL;
    B_S3 : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Pulse : BOOL;
    A_Armed : BOOL;
    B_Vote : BOOL;
    B_Unanimous : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PrevSignal : BOOL := FALSE;
END_VAR

A_Pulse := A_Arm AND (NOT A_Signal) AND A_PrevSignal;
A_Armed := A_Arm;
A_PrevSignal := A_Signal;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Pulse THEN
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
