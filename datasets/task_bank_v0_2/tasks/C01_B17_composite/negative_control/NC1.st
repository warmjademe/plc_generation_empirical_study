FUNCTION_BLOCK C01_B17_composite
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
    B_Info : BOOL;
    B_Warning : BOOL;
    B_Trip : BOOL;
    B_Emergency : BOOL;
    B_Suppress : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_RunPermit : BOOL;
    A_Degraded : BOOL;
    A_BypassActive : BOOL;
    A_Blocked : BOOL;
    B_Active : BOOL;
    B_Level : INT;
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
    A_BypassActive := FALSE;
END_IF;
A_RunPermit := A_SelectedRequest AND A_SafetyOK AND (A_VoteOK OR A_BypassActive);
A_Degraded := A_RunPermit AND ((NOT A_Unanimous) OR A_BypassActive);
A_Blocked := A_SelectedRequest AND (NOT A_RunPermit);

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_RunPermit THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

IF SubsystemBEnable AND CrossReady THEN
    IF B_Emergency THEN
        B_Level := 4;
        B_Active := TRUE;
    ELSIF B_Suppress THEN
        B_Level := 0;
        B_Active := FALSE;
    ELSIF B_Trip THEN
        B_Level := 3;
        B_Active := TRUE;
    ELSIF B_Warning THEN
        B_Level := 2;
        B_Active := TRUE;
    ELSIF B_Info THEN
        B_Level := 1;
        B_Active := TRUE;
    ELSE
        B_Level := 0;
        B_Active := FALSE;
    END_IF;
ELSE
    B_Active := FALSE;
    B_Level := 0;
END_IF;

END_FUNCTION_BLOCK
