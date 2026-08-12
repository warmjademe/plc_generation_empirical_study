FUNCTION_BLOCK C04_S13_lean_composite
VAR_INPUT
    A_S1 : BOOL;
    A_S2 : BOOL;
    A_S3 : BOOL;
    B_Signal : BOOL;
    B_Arm : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Vote : BOOL;
    A_Unanimous : BOOL;
    B_Pulse : BOOL;
    B_Armed : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    B_PrevSignal : BOOL := FALSE;
END_VAR

A_Vote := (A_S1 AND A_S2) OR (A_S1 AND A_S3) OR (A_S2 AND A_S3);
A_Unanimous := (A_S1 AND A_S2 AND A_S3) OR ((NOT A_S1) AND (NOT A_S2) AND (NOT A_S3));

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Vote THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := FALSE;

IF SubsystemBEnable AND CrossReady THEN
    B_Pulse := B_Arm AND (NOT B_Signal) AND B_PrevSignal;
    B_Armed := B_Arm;
    B_PrevSignal := B_Signal;
ELSE
    B_Pulse := FALSE;
    B_Armed := FALSE;
END_IF;

END_FUNCTION_BLOCK
