FUNCTION_BLOCK C06_U21_lean_composite
VAR_INPUT
    A_ItemPulse : BOOL;
    A_Rejected : BOOL;
    A_Stop : BOOL;
    A_Reset : BOOL;
    A_Target : INT;
    A_RejectLimit : INT;
    B_Info : BOOL;
    B_Warning : BOOL;
    B_Trip : BOOL;
    B_Emergency : BOOL;
    B_Suppress : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_AcceptedCount : INT;
    A_RejectCount : INT;
    A_ConsecutiveRejects : INT;
    A_Complete : BOOL;
    A_LockedOut : BOOL;
    B_Active : BOOL;
    B_Level : INT;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PrevItem : BOOL;
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
CrossBlocked := FALSE;

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
