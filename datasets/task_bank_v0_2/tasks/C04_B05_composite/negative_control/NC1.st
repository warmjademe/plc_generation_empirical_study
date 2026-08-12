FUNCTION_BLOCK C04_B05_composite
VAR_INPUT
    A_EventA : BOOL;
    A_EventB : BOOL;
    A_Arm : BOOL;
    A_Reset : BOOL;
    B_Event : BOOL;
    B_Qualify : BOOL;
    B_Reset : BOOL;
    B_MaxCount : INT;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Captured : BOOL;
    A_Code : INT;
    A_Pulse : BOOL;
    B_Count : INT;
    B_AcceptedPulse : BOOL;
    B_AtLimit : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PrevA : BOOL := FALSE;
    A_PrevB : BOOL := FALSE;
    B_PrevEvent : BOOL := FALSE;
END_VAR

A_Pulse := FALSE;
IF A_Reset THEN
    A_Captured := FALSE;
    A_Code := 0;
ELSIF A_Arm AND (NOT A_Captured) THEN
    IF A_EventA AND (NOT A_PrevA) THEN
        A_Captured := FALSE;
        A_Code := 1;
        A_Pulse := TRUE;
    ELSIF A_EventB AND (NOT A_PrevB) THEN
        A_Captured := TRUE;
        A_Code := 2;
        A_Pulse := TRUE;
    END_IF;
END_IF;
A_PrevA := A_EventA;
A_PrevB := A_EventB;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Captured THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

IF SubsystemBEnable AND CrossReady THEN
    B_AcceptedPulse := FALSE;
    IF B_Reset THEN
        B_Count := 0;
    ELSIF B_Event AND (NOT B_PrevEvent) AND B_Qualify AND (B_Count < B_MaxCount) THEN
        B_Count := B_Count + 1;
        B_AcceptedPulse := TRUE;
    END_IF;
    B_AtLimit := B_Count >= B_MaxCount;
    B_PrevEvent := B_Event;
ELSE
    B_Count := 0;
    B_AcceptedPulse := FALSE;
    B_AtLimit := FALSE;
END_IF;

END_FUNCTION_BLOCK
