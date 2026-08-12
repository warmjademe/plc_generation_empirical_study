FUNCTION_BLOCK C04_R03_lean_composite
VAR_INPUT
    A_Event : BOOL;
    A_Qualify : BOOL;
    A_Reset : BOOL;
    A_MaxCount : INT;
    B_S1 : BOOL;
    B_S2 : BOOL;
    B_S3 : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Count : INT;
    A_AcceptedPulse : BOOL;
    A_AtLimit : BOOL;
    B_Vote : BOOL;
    B_Unanimous : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PrevEvent : BOOL := FALSE;
END_VAR

A_AcceptedPulse := FALSE;
IF A_Reset THEN
    A_Count := 0;
ELSIF A_Event AND (NOT A_PrevEvent) AND A_Qualify AND (A_Count < A_MaxCount) THEN
    A_Count := A_Count + 1;
    A_AcceptedPulse := TRUE;
END_IF;
A_AtLimit := A_Count >= A_MaxCount;
A_PrevEvent := A_Event;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_AcceptedPulse THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := FALSE;

IF SubsystemBEnable AND CrossReady THEN
    B_Vote := (B_S1 AND B_S2) OR (B_S1 AND B_S3) OR (B_S2 AND B_S3);
    B_Unanimous := (B_S1 AND B_S2 AND B_S3) OR ((NOT B_S1) AND (NOT B_S2) AND (NOT B_S3));
ELSE
    B_Vote := FALSE;
    B_Unanimous := FALSE;
END_IF;

END_FUNCTION_BLOCK
