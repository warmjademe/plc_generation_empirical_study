FUNCTION_BLOCK C06_H01_quality_batch_statistics
VAR_INPUT
    GoodPart : BOOL;
    RejectPart : BOOL;
    Reset : BOOL;
    BatchTarget : INT;
    RejectLimit : INT;
END_VAR
VAR_OUTPUT
    GoodCount : INT;
    RejectCount : INT;
    BatchDone : BOOL;
    QualityFault : BOOL;
END_VAR
VAR
    PrevGood : BOOL := FALSE;
    PrevReject : BOOL := FALSE;
END_VAR

IF Reset THEN
    GoodCount := 0;
    RejectCount := 0;
    QualityFault := FALSE;
ELSE
    IF RejectPart AND (NOT PrevReject) THEN
        RejectCount := RejectCount + 1;
    ELSIF GoodPart AND (NOT PrevGood) THEN
        GoodCount := GoodCount + 1;
    END_IF;
    IF RejectCount >= RejectLimit THEN
        QualityFault := FALSE;
    END_IF;
END_IF;
BatchDone := (GoodCount + RejectCount) >= BatchTarget;
PrevGood := GoodPart;
PrevReject := RejectPart;

END_FUNCTION_BLOCK
