FUNCTION_BLOCK C04_R20_lean_composite
VAR_INPUT
    A_Button : BOOL;
    A_Enable : BOOL;
    A_Reset : BOOL;
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
    A_State : BOOL;
    A_AcceptedPulse : BOOL;
    B_RunPermit : BOOL;
    B_Degraded : BOOL;
    B_BypassActive : BOOL;
    B_Blocked : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PrevButton : BOOL := FALSE;
    B_SelectedRequest : BOOL;
    B_VoteOK : BOOL;
    B_AnyChannel : BOOL;
    B_Unanimous : BOOL;
END_VAR

A_AcceptedPulse := FALSE;
IF A_Reset THEN
    A_State := FALSE;
ELSIF A_Enable AND A_Button AND (NOT A_PrevButton) THEN
    A_State := NOT A_State;
    A_AcceptedPulse := TRUE;
END_IF;
A_PrevButton := A_Button;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_State THEN
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
