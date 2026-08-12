FUNCTION_BLOCK C06_R02_lean_composite
VAR_INPUT
    A_GoodPart : BOOL;
    A_RejectPart : BOOL;
    A_Reset : BOOL;
    A_BatchTarget : INT;
    A_RejectLimit : INT;
    B_ChA : BOOL;
    B_ChB : BOOL;
    B_TestMode : BOOL;
    B_TestPermit : BOOL;
    B_ProcessRequest : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_GoodCount : INT;
    A_RejectCount : INT;
    A_BatchDone : BOOL;
    A_QualityFault : BOOL;
    B_SafeEnable : BOOL;
    B_Disagree : BOOL;
    B_TestActive : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PrevGood : BOOL := FALSE;
    A_PrevReject : BOOL := FALSE;
END_VAR

IF A_Reset THEN
    A_GoodCount := 0;
    A_RejectCount := 0;
    A_QualityFault := FALSE;
ELSE
    IF A_RejectPart AND (NOT A_PrevReject) THEN
        A_RejectCount := A_RejectCount + 1;
    ELSIF A_GoodPart AND (NOT A_PrevGood) THEN
        A_GoodCount := A_GoodCount + 1;
    END_IF;
    IF A_RejectCount >= A_RejectLimit THEN
        A_QualityFault := TRUE;
    END_IF;
END_IF;
A_BatchDone := (A_GoodCount + A_RejectCount) >= A_BatchTarget;
A_PrevGood := A_GoodPart;
A_PrevReject := A_RejectPart;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_BatchDone THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := FALSE;

IF SubsystemBEnable AND CrossReady THEN
    B_Disagree := B_ChA <> B_ChB;
    B_TestActive := B_TestMode AND B_TestPermit;
    IF B_TestMode THEN
        B_SafeEnable := B_ProcessRequest AND B_TestPermit AND B_ChA;
    ELSE
        B_SafeEnable := B_ProcessRequest AND B_ChA AND B_ChB;
    END_IF;
ELSE
    B_SafeEnable := FALSE;
    B_Disagree := FALSE;
    B_TestActive := FALSE;
END_IF;

END_FUNCTION_BLOCK
