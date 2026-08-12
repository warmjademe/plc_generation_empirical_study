FUNCTION_BLOCK C06_R05_lean_composite
VAR_INPUT
    A_GoodPart : BOOL;
    A_RejectPart : BOOL;
    A_Reset : BOOL;
    A_BatchTarget : INT;
    A_RejectLimit : INT;
    B_Ch1 : BOOL;
    B_Ch2 : BOOL;
    B_Ch3 : BOOL;
    B_AutoMode : BOOL;
    B_AutoRequest : BOOL;
    B_ManualRequest : BOOL;
    B_BypassRequest : BOOL;
    B_BypassPermit : BOOL;
    B_SafetyOK : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_GoodCount : INT;
    A_RejectCount : INT;
    A_BatchDone : BOOL;
    A_QualityFault : BOOL;
    B_RunPermit : BOOL;
    B_Degraded : BOOL;
    B_BypassActive : BOOL;
    B_Blocked : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PrevGood : BOOL := FALSE;
    A_PrevReject : BOOL := FALSE;
    B_SelectedRequest : BOOL;
    B_VoteOK : BOOL;
    B_AnyChannel : BOOL;
    B_Unanimous : BOOL;
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
    B_SelectedRequest := (B_AutoMode AND B_AutoRequest) OR ((NOT B_AutoMode) AND B_ManualRequest);
    B_VoteOK := (B_Ch1 AND B_Ch2) OR (B_Ch1 AND B_Ch3) OR (B_Ch2 AND B_Ch3);
    B_AnyChannel := B_Ch1 OR B_Ch2 OR B_Ch3;
    B_Unanimous := (B_Ch1 AND B_Ch2 AND B_Ch3) OR ((NOT B_Ch1) AND (NOT B_Ch2) AND (NOT B_Ch3));
    IF B_Reset AND (NOT B_AutoRequest) AND (NOT B_ManualRequest) THEN
        B_BypassActive := FALSE;
    ELSIF (NOT B_AutoMode) AND B_BypassRequest AND B_BypassPermit AND B_SafetyOK AND B_AnyChannel THEN
        B_BypassActive := TRUE;
    END_IF;
    B_RunPermit := B_SelectedRequest AND B_SafetyOK AND (B_VoteOK OR B_BypassActive);
    B_Degraded := B_RunPermit AND ((NOT B_Unanimous) OR B_BypassActive);
    B_Blocked := B_SelectedRequest AND (NOT B_RunPermit);
ELSE
    B_RunPermit := FALSE;
    B_Degraded := FALSE;
    B_BypassActive := FALSE;
    B_Blocked := FALSE;
END_IF;

END_FUNCTION_BLOCK
