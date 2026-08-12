FUNCTION_BLOCK C06_W01_lean_composite
VAR_INPUT
    A_Info : BOOL;
    A_Warning : BOOL;
    A_Trip : BOOL;
    A_Emergency : BOOL;
    A_Suppress : BOOL;
    B_GoodPart : BOOL;
    B_RejectPart : BOOL;
    B_Reset : BOOL;
    B_BatchTarget : INT;
    B_RejectLimit : INT;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Active : BOOL;
    A_Level : INT;
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

IF A_Emergency THEN
    A_Level := 4;
    A_Active := TRUE;
ELSIF A_Suppress THEN
    A_Level := 0;
    A_Active := FALSE;
ELSIF A_Trip THEN
    A_Level := 3;
    A_Active := TRUE;
ELSIF A_Warning THEN
    A_Level := 2;
    A_Active := TRUE;
ELSIF A_Info THEN
    A_Level := 1;
    A_Active := TRUE;
ELSE
    A_Level := 0;
    A_Active := FALSE;
END_IF;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Active THEN
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
