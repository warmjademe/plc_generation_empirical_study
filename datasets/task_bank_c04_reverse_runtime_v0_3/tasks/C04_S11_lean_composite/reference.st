FUNCTION_BLOCK C04_S11_lean_composite
VAR_INPUT
    A_S1 : BOOL;
    A_S2 : BOOL;
    A_S3 : BOOL;
    B_Event : BOOL;
    B_Qualify : BOOL;
    B_Reset : BOOL;
    B_MaxCount : INT;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Vote : BOOL;
    A_Unanimous : BOOL;
    B_Count : INT;
    B_AcceptedPulse : BOOL;
    B_AtLimit : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    B_PrevEvent : BOOL := FALSE;
END_VAR

A_Vote := (A_S1 AND A_S2) OR (A_S1 AND A_S3) OR (A_S2 AND A_S3);
A_Unanimous := (A_S1 AND A_S2 AND A_S3) OR ((NOT A_S1) AND (NOT A_S2) AND (NOT A_S3));

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Vote THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

IF SubsystemBEnable AND CrossReady THEN
    B_AcceptedPulse := FALSE;
    IF B_Reset THEN
        B_Count := 0;
    ELSIF B_Event AND (NOT B_PrevEvent) AND B_Qualify AND (B_Count < B_MaxCount) THEN
        B_Count := B_Count + 1;
        B_AcceptedPulse := TRUE;
    END_IF;
    B_AtLimit := B_Count >= B_MaxCount;
    B_PrevEvent := B_Event;
ELSE
    B_Count := 0;
    B_AcceptedPulse := FALSE;
    B_AtLimit := FALSE;
END_IF;

END_FUNCTION_BLOCK
