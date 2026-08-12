FUNCTION_BLOCK C06_B05_composite
VAR_INPUT
    A_Inspected : BOOL;
    A_Rejected : BOOL;
    A_Reset : BOOL;
    A_WindowSize : INT;
    A_RejectLimit : INT;
    B_GoodPart : BOOL;
    B_RejectPart : BOOL;
    B_Reset : BOOL;
    B_BatchTarget : INT;
    B_RejectLimit : INT;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_WindowCount : INT;
    A_RejectCount : INT;
    A_LockedOut : BOOL;
    A_WindowComplete : BOOL;
    B_GoodCount : INT;
    B_RejectCount : INT;
    B_BatchDone : BOOL;
    B_QualityFault : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PrevInspected : BOOL := FALSE;
    B_PrevGood : BOOL := FALSE;
    B_PrevReject : BOOL := FALSE;
END_VAR

A_WindowComplete := FALSE;
IF A_Reset THEN
    A_WindowCount := 0;
    A_RejectCount := 0;
    A_LockedOut := FALSE;
ELSIF (NOT A_LockedOut) AND A_Inspected AND (NOT A_PrevInspected) THEN
    A_WindowCount := A_WindowCount + 1;
    IF A_Rejected THEN
        A_RejectCount := A_RejectCount + 1;
    END_IF;
    IF A_WindowCount >= A_WindowSize THEN
        IF A_RejectCount > A_RejectLimit THEN
            A_LockedOut := TRUE;
        END_IF;
        A_WindowCount := 0;
        A_RejectCount := 0;
        A_WindowComplete := TRUE;
    END_IF;
END_IF;
A_PrevInspected := A_Inspected;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_LockedOut THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

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
