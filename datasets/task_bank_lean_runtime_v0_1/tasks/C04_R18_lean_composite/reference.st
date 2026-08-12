FUNCTION_BLOCK C04_R18_lean_composite
VAR_INPUT
    A_Button : BOOL;
    A_Enable : BOOL;
    A_Reset : BOOL;
    B_S1 : BOOL;
    B_S2 : BOOL;
    B_S3 : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_State : BOOL;
    A_AcceptedPulse : BOOL;
    B_Vote : BOOL;
    B_Unanimous : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PrevButton : BOOL := FALSE;
END_VAR

A_AcceptedPulse := FALSE;
IF A_Reset THEN
    A_State := FALSE;
ELSIF A_Enable AND A_Button AND (NOT A_PrevButton) THEN
    A_State := NOT A_State;
    A_AcceptedPulse := TRUE;
END_IF;
A_PrevButton := A_Button;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_State THEN
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
