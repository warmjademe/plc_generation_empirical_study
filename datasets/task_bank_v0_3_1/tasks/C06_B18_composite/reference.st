FUNCTION_BLOCK C06_B18_composite
VAR_INPUT
    A_ItemPulse : BOOL;
    A_Rejected : BOOL;
    A_Stop : BOOL;
    A_Reset : BOOL;
    A_Target : INT;
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
    A_AcceptedCount : INT;
    A_RejectCount : INT;
    A_ConsecutiveRejects : INT;
    A_Complete : BOOL;
    A_LockedOut : BOOL;
    B_WindowCount : INT;
    B_RejectCount : INT;
    B_LockedOut : BOOL;
    B_WindowComplete : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PrevItem : BOOL;
    B_PrevInspected : BOOL := FALSE;
END_VAR

IF A_Reset AND A_Stop AND (NOT A_ItemPulse) THEN
    A_AcceptedCount := 0;
    A_RejectCount := 0;
    A_ConsecutiveRejects := 0;
    A_Complete := FALSE;
    A_LockedOut := FALSE;
ELSIF A_RejectLimit <= 0 THEN
    A_LockedOut := TRUE;
ELSIF A_ItemPulse AND (NOT A_PrevItem) AND (NOT A_Stop) AND (NOT A_Complete) AND (NOT A_LockedOut) THEN
    IF A_Rejected THEN
        A_RejectCount := A_RejectCount + 1;
        A_ConsecutiveRejects := A_ConsecutiveRejects + 1;
        IF A_ConsecutiveRejects >= A_RejectLimit THEN A_LockedOut := TRUE; END_IF;
    ELSE
        A_AcceptedCount := A_AcceptedCount + 1;
        A_ConsecutiveRejects := 0;
        IF (A_Target > 0) AND (A_AcceptedCount >= A_Target) THEN A_Complete := TRUE; END_IF;
    END_IF;
END_IF;
A_PrevItem := A_ItemPulse;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Complete THEN
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
