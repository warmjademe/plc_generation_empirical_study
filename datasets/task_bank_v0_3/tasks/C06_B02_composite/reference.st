FUNCTION_BLOCK C06_B02_composite
VAR_INPUT
    A_GoodPart : BOOL;
    A_RejectPart : BOOL;
    A_Reset : BOOL;
    A_BatchTarget : INT;
    A_RejectLimit : INT;
    B_Item : BOOL;
    B_Reset : BOOL;
    B_Target : INT;
    B_Enable : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_GoodCount : INT;
    A_RejectCount : INT;
    A_BatchDone : BOOL;
    A_QualityFault : BOOL;
    B_Count : INT;
    B_BatchDone : BOOL;
    B_Accepted : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PrevGood : BOOL := FALSE;
    A_PrevReject : BOOL := FALSE;
    B_PrevItem : BOOL := FALSE;
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
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

IF SubsystemBEnable AND CrossReady THEN
    B_Accepted := FALSE;
    IF B_Reset THEN
        B_Count := 0;
    ELSIF B_Enable AND B_Item AND (NOT B_PrevItem) AND (B_Count < B_Target) THEN
        B_Count := B_Count + 1;
        B_Accepted := TRUE;
    END_IF;
    B_BatchDone := B_Count >= B_Target;
    B_PrevItem := B_Item;
ELSE
    B_Count := 0;
    B_BatchDone := FALSE;
    B_Accepted := FALSE;
END_IF;

END_FUNCTION_BLOCK
