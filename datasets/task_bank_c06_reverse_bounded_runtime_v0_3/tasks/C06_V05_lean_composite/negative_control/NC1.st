FUNCTION_BLOCK C06_V05_lean_composite
VAR_INPUT
    A_Info : BOOL;
    A_Warning : BOOL;
    A_Trip : BOOL;
    A_Emergency : BOOL;
    A_Suppress : BOOL;
    B_ItemPulse : BOOL;
    B_Rejected : BOOL;
    B_Stop : BOOL;
    B_Reset : BOOL;
    B_Target : INT;
    B_RejectLimit : INT;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Active : BOOL;
    A_Level : INT;
    B_AcceptedCount : INT;
    B_RejectCount : INT;
    B_ConsecutiveRejects : INT;
    B_Complete : BOOL;
    B_LockedOut : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    B_PrevItem : BOOL;
END_VAR

IF A_Emergency THEN
    A_Level := 4;
    A_Active := TRUE;
ELSIF A_Suppress THEN
    A_Level := 0;
    A_Active := FALSE;
ELSIF A_Trip THEN
    A_Level := 3;
    A_Active := TRUE;
ELSIF A_Warning THEN
    A_Level := 2;
    A_Active := TRUE;
ELSIF A_Info THEN
    A_Level := 1;
    A_Active := TRUE;
ELSE
    A_Level := 0;
    A_Active := FALSE;
END_IF;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Active THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := FALSE;

IF SubsystemBEnable AND CrossReady THEN
    IF B_Reset AND B_Stop AND (NOT B_ItemPulse) THEN
        B_AcceptedCount := 0;
        B_RejectCount := 0;
        B_ConsecutiveRejects := 0;
        B_Complete := FALSE;
        B_LockedOut := FALSE;
    ELSIF B_RejectLimit <= 0 THEN
        B_LockedOut := TRUE;
    ELSIF B_ItemPulse AND (NOT B_PrevItem) AND (NOT B_Stop) AND (NOT B_Complete) AND (NOT B_LockedOut) THEN
        IF B_Rejected THEN
            B_RejectCount := B_RejectCount + 1;
            B_ConsecutiveRejects := B_ConsecutiveRejects + 1;
            IF B_ConsecutiveRejects >= B_RejectLimit THEN B_LockedOut := TRUE; END_IF;
        ELSE
            B_AcceptedCount := B_AcceptedCount + 1;
            B_ConsecutiveRejects := 0;
            IF (B_Target > 0) AND (B_AcceptedCount >= B_Target) THEN B_Complete := TRUE; END_IF;
        END_IF;
    END_IF;
    B_PrevItem := B_ItemPulse;
ELSE
    B_AcceptedCount := 0;
    B_RejectCount := 0;
    B_ConsecutiveRejects := 0;
    B_Complete := FALSE;
    B_LockedOut := FALSE;
END_IF;

END_FUNCTION_BLOCK
