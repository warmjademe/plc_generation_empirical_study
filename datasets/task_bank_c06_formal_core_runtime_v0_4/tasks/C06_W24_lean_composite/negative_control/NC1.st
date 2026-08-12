FUNCTION_BLOCK C06_W24_lean_composite
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
    B_AddItem : BOOL;
    B_RemoveItem : BOOL;
    B_Reset : BOOL;
    B_Capacity : INT;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_RunPermit : BOOL;
    A_Degraded : BOOL;
    A_BypassActive : BOOL;
    A_Blocked : BOOL;
    B_Count : INT;
    B_Empty : BOOL;
    B_Full : BOOL;
    B_Conflict : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_SelectedRequest : BOOL;
    A_VoteOK : BOOL;
    A_AnyChannel : BOOL;
    A_Unanimous : BOOL;
    B_PrevAdd : BOOL := FALSE;
    B_PrevRemove : BOOL := FALSE;
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
    B_Conflict := FALSE;
    IF B_Reset THEN
        B_Count := 0;
    ELSIF B_AddItem AND (NOT B_PrevAdd) AND B_RemoveItem AND (NOT B_PrevRemove) THEN
        B_Conflict := TRUE;
    ELSIF B_AddItem AND (NOT B_PrevAdd) AND (B_Count < B_Capacity) THEN
        B_Count := B_Count + 1;
    ELSIF B_RemoveItem AND (NOT B_PrevRemove) AND (B_Count > 0) THEN
        B_Count := B_Count - 1;
    END_IF;
    B_Empty := B_Count = 0;
    B_Full := B_Count >= B_Capacity;
    B_PrevAdd := B_AddItem;
    B_PrevRemove := B_RemoveItem;
ELSE
    B_Count := 0;
    B_Empty := FALSE;
    B_Full := FALSE;
    B_Conflict := FALSE;
END_IF;

END_FUNCTION_BLOCK
