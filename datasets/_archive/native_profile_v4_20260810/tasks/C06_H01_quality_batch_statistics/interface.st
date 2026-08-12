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
END_FUNCTION_BLOCK
