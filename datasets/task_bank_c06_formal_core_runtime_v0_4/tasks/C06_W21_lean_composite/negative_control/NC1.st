FUNCTION_BLOCK C06_W21_lean_composite
VAR_INPUT
    A_Ch1 : BOOL;
    A_Ch2 : BOOL;
    A_Ch3 : BOOL;
    A_AutoMode : BOOL;
    A_AutoRequest : BOOL;
    A_ManualRequest : BOOL;
    A_BypassRequest : BOOL;
    A_BypassPermit : BOOL;
    A_SafetyOK : BOOL;
    A_Reset : BOOL;
    B_GoodPart : BOOL;
    B_RejectPart : BOOL;
    B_Reset : BOOL;
    B_BatchTarget : INT;
    B_RejectLimit : INT;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_RunPermit : BOOL;
    A_Degraded : BOOL;
    A_BypassActive : BOOL;
    A_Blocked : BOOL;
    B_GoodCount : INT;
    B_RejectCount : INT;
    B_BatchDone : BOOL;
    B_QualityFault : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_SelectedRequest : BOOL;
    A_VoteOK : BOOL;
    A_AnyChannel : BOOL;
    A_Unanimous : BOOL;
    B_PrevGood : BOOL := FALSE;
    B_PrevReject : BOOL := FALSE;
END_VAR

A_SelectedRequest := (A_AutoMode AND A_AutoRequest) OR ((NOT A_AutoMode) AND A_ManualRequest);
A_VoteOK := (A_Ch1 AND A_Ch2) OR (A_Ch1 AND A_Ch3) OR (A_Ch2 AND A_Ch3);
A_AnyChannel := A_Ch1 OR A_Ch2 OR A_Ch3;
A_Unanimous := (A_Ch1 AND A_Ch2 AND A_Ch3) OR ((NOT A_Ch1) AND (NOT A_Ch2) AND (NOT A_Ch3));
IF A_Reset AND (NOT A_AutoRequest) AND (NOT A_ManualRequest) THEN
    A_BypassActive := FALSE;
ELSIF (NOT A_AutoMode) AND A_BypassRequest AND A_BypassPermit AND A_SafetyOK AND A_AnyChannel THEN
    A_BypassActive := TRUE;
END_IF;
A_RunPermit := A_SelectedRequest AND A_SafetyOK AND (A_VoteOK OR A_BypassActive);
A_Degraded := A_RunPermit AND ((NOT A_Unanimous) OR A_BypassActive);
A_Blocked := A_SelectedRequest AND (NOT A_RunPermit);

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_RunPermit THEN
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
