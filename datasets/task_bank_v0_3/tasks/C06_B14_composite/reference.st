FUNCTION_BLOCK C06_B14_composite
VAR_INPUT
    A_AddItem : BOOL;
    A_RemoveItem : BOOL;
    A_Reset : BOOL;
    A_Capacity : INT;
    B_Inspected : BOOL;
    B_Rejected : BOOL;
    B_Reset : BOOL;
    B_WindowSize : INT;
    B_RejectLimit : INT;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Count : INT;
    A_Empty : BOOL;
    A_Full : BOOL;
    A_Conflict : BOOL;
    B_WindowCount : INT;
    B_RejectCount : INT;
    B_LockedOut : BOOL;
    B_WindowComplete : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PrevAdd : BOOL := FALSE;
    A_PrevRemove : BOOL := FALSE;
    B_PrevInspected : BOOL := FALSE;
END_VAR

A_Conflict := FALSE;
IF A_Reset THEN
    A_Count := 0;
ELSIF A_AddItem AND (NOT A_PrevAdd) AND A_RemoveItem AND (NOT A_PrevRemove) THEN
    A_Conflict := TRUE;
ELSIF A_AddItem AND (NOT A_PrevAdd) AND (A_Count < A_Capacity) THEN
    A_Count := A_Count + 1;
ELSIF A_RemoveItem AND (NOT A_PrevRemove) AND (A_Count > 0) THEN
    A_Count := A_Count - 1;
END_IF;
A_Empty := A_Count = 0;
A_Full := A_Count >= A_Capacity;
A_PrevAdd := A_AddItem;
A_PrevRemove := A_RemoveItem;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Empty THEN
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
