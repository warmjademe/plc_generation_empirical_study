FUNCTION_BLOCK C01_B16_composite
VAR_INPUT
    A_AutoMode : BOOL;
    A_AutoDemand : BOOL;
    A_ManualDemand : BOOL;
    A_SafetyOK : BOOL;
    A_Inhibit : BOOL;
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
    A_Command : BOOL;
    A_Blocked : BOOL;
    B_RunPermit : BOOL;
    B_Degraded : BOOL;
    B_BypassActive : BOOL;
    B_Blocked : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    B_SelectedRequest : BOOL;
    B_VoteOK : BOOL;
    B_AnyChannel : BOOL;
    B_Unanimous : BOOL;
END_VAR

A_Command := ((A_AutoMode AND A_AutoDemand) OR ((NOT A_AutoMode) AND A_ManualDemand))
           AND A_SafetyOK AND (NOT A_Inhibit);
A_Blocked := ((A_AutoMode AND A_AutoDemand) OR ((NOT A_AutoMode) AND A_ManualDemand))
           AND ((NOT A_SafetyOK) OR A_Inhibit);

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Command THEN
    CrossReady := FALSE;
END_IF;
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

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
