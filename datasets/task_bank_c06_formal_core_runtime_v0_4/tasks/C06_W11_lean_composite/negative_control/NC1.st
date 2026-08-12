FUNCTION_BLOCK C06_W11_lean_composite
VAR_INPUT
    A_S1 : BOOL;
    A_S2 : BOOL;
    A_S3 : BOOL;
    B_GoodPart : BOOL;
    B_RejectPart : BOOL;
    B_Reset : BOOL;
    B_BatchTarget : INT;
    B_RejectLimit : INT;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Vote : BOOL;
    A_Unanimous : BOOL;
    B_GoodCount : INT;
    B_RejectCount : INT;
    B_BatchDone : BOOL;
    B_QualityFault : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    B_PrevGood : BOOL := FALSE;
    B_PrevReject : BOOL := FALSE;
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
    IF B_Reset THEN
        B_GoodCount := 0;
        B_RejectCount := 0;
        B_QualityFault := FALSE;
    ELSE
        IF B_RejectPart AND (NOT B_PrevReject) THEN
            B_RejectCount := B_RejectCount + 1;
        ELSIF B_GoodPart AND (NOT B_PrevGood) THEN
            B_GoodCount := B_GoodCount + 1;
        END_IF;
        IF B_RejectCount >= B_RejectLimit THEN
            B_QualityFault := TRUE;
        END_IF;
    END_IF;
    B_BatchDone := (B_GoodCount + B_RejectCount) >= B_BatchTarget;
    B_PrevGood := B_GoodPart;
    B_PrevReject := B_RejectPart;
ELSE
    B_GoodCount := 0;
    B_RejectCount := 0;
    B_BatchDone := FALSE;
    B_QualityFault := FALSE;
END_IF;

END_FUNCTION_BLOCK
