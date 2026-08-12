FUNCTION_BLOCK C06_B01_composite
VAR_INPUT
    A_GoodPart : BOOL;
    A_RejectPart : BOOL;
    A_Reset : BOOL;
    A_BatchTarget : INT;
    A_RejectLimit : INT;
    B_Inspected : BOOL;
    B_Rejected : BOOL;
    B_Reset : BOOL;
    B_WindowSize : INT;
    B_RejectLimit : INT;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_GoodCount : INT;
    A_RejectCount : INT;
    A_BatchDone : BOOL;
    A_QualityFault : BOOL;
    B_WindowCount : INT;
    B_RejectCount : INT;
    B_LockedOut : BOOL;
    B_WindowComplete : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PrevGood : BOOL := FALSE;
    A_PrevReject : BOOL := FALSE;
    B_PrevInspected : BOOL := FALSE;
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
