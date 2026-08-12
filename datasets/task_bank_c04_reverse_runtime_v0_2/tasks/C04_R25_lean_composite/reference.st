FUNCTION_BLOCK C04_R25_lean_composite
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
    B_EventA : BOOL;
    B_EventB : BOOL;
    B_Qualify : BOOL;
    B_Inhibit : BOOL;
    B_Reset : BOOL;
    B_MaxCount : INT;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_RunPermit : BOOL;
    A_Degraded : BOOL;
    A_BypassActive : BOOL;
    A_Blocked : BOOL;
    B_PulseA : BOOL;
    B_PulseB : BOOL;
    B_Count : INT;
    B_Locked : BOOL;
    B_LastSource : INT;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_SelectedRequest : BOOL;
    A_VoteOK : BOOL;
    A_AnyChannel : BOOL;
    A_Unanimous : BOOL;
    B_PrevA : BOOL;
    B_PrevB : BOOL;
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
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

IF SubsystemBEnable AND CrossReady THEN
    B_PulseA := FALSE;
    B_PulseB := FALSE;
    IF B_Reset AND (NOT B_EventA) AND (NOT B_EventB) THEN
        B_Count := 0;
        B_Locked := FALSE;
        B_LastSource := 0;
    ELSIF B_MaxCount <= 0 THEN
        B_Locked := TRUE;
    ELSIF B_Qualify AND (NOT B_Inhibit) AND (NOT B_Locked) THEN
        IF B_EventA AND (NOT B_PrevA) THEN
            B_PulseA := TRUE;
            B_Count := B_Count + 1;
            B_LastSource := 1;
        ELSIF B_EventB AND (NOT B_PrevB) THEN
            B_PulseB := TRUE;
            B_Count := B_Count + 1;
            B_LastSource := 2;
        END_IF;
        IF B_Count >= B_MaxCount THEN B_Count := B_MaxCount; B_Locked := TRUE; END_IF;
    END_IF;
    B_PrevA := B_EventA;
    B_PrevB := B_EventB;
ELSE
    B_PulseA := FALSE;
    B_PulseB := FALSE;
    B_Count := 0;
    B_Locked := FALSE;
    B_LastSource := 0;
END_IF;

END_FUNCTION_BLOCK
