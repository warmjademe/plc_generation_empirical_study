FUNCTION_BLOCK C01_B19_composite
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
    B_S1 : BOOL;
    B_S2 : BOOL;
    B_S3 : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_RunPermit : BOOL;
    A_Degraded : BOOL;
    A_BypassActive : BOOL;
    A_Blocked : BOOL;
    B_Vote : BOOL;
    B_Unanimous : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_SelectedRequest : BOOL;
    A_VoteOK : BOOL;
    A_AnyChannel : BOOL;
    A_Unanimous : BOOL;
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
    B_Vote := (B_S1 AND B_S2) OR (B_S1 AND B_S3) OR (B_S2 AND B_S3);
    B_Unanimous := (B_S1 AND B_S2 AND B_S3) OR ((NOT B_S1) AND (NOT B_S2) AND (NOT B_S3));
ELSE
    B_Vote := FALSE;
    B_Unanimous := FALSE;
END_IF;

END_FUNCTION_BLOCK
