FUNCTION_BLOCK C06_V12_lean_composite
VAR_INPUT
    A_S1 : BOOL;
    A_S2 : BOOL;
    A_S3 : BOOL;
    B_Inspected : BOOL;
    B_Rejected : BOOL;
    B_Reset : BOOL;
    B_WindowSize : INT;
    B_RejectLimit : INT;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Vote : BOOL;
    A_Unanimous : BOOL;
    B_WindowCount : INT;
    B_RejectCount : INT;
    B_LockedOut : BOOL;
    B_WindowComplete : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    B_PrevInspected : BOOL := FALSE;
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
    B_WindowComplete := FALSE;
    IF B_Reset THEN
        B_WindowCount := 0;
        B_RejectCount := 0;
        B_LockedOut := FALSE;
    ELSIF (NOT B_LockedOut) AND B_Inspected AND (NOT B_PrevInspected) THEN
        B_WindowCount := B_WindowCount + 1;
        IF B_Rejected THEN
            B_RejectCount := B_RejectCount + 1;
        END_IF;
        IF B_WindowCount >= B_WindowSize THEN
            IF B_RejectCount > B_RejectLimit THEN
                B_LockedOut := TRUE;
            END_IF;
            B_WindowCount := 0;
            B_RejectCount := 0;
            B_WindowComplete := TRUE;
        END_IF;
    END_IF;
    B_PrevInspected := B_Inspected;
ELSE
    B_WindowCount := 0;
    B_RejectCount := 0;
    B_LockedOut := FALSE;
    B_WindowComplete := FALSE;
END_IF;

END_FUNCTION_BLOCK
