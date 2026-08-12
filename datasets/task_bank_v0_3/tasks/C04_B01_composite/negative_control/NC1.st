FUNCTION_BLOCK C04_B01_composite
VAR_INPUT
    A_Event : BOOL;
    A_Qualify : BOOL;
    A_Reset : BOOL;
    A_MaxCount : INT;
    B_EventA : BOOL;
    B_EventB : BOOL;
    B_Arm : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Count : INT;
    A_AcceptedPulse : BOOL;
    A_AtLimit : BOOL;
    B_Captured : BOOL;
    B_Code : INT;
    B_Pulse : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PrevEvent : BOOL := FALSE;
    B_PrevA : BOOL := FALSE;
    B_PrevB : BOOL := FALSE;
END_VAR

A_AcceptedPulse := FALSE;
IF A_Reset THEN
    A_Count := 0;
ELSIF A_Event AND (NOT A_PrevEvent) AND A_Qualify AND (A_Count < A_MaxCount) THEN
    A_Count := A_Count + 1;
    A_AcceptedPulse := FALSE;
END_IF;
A_AtLimit := A_Count >= A_MaxCount;
A_PrevEvent := A_Event;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_AcceptedPulse THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

IF SubsystemBEnable AND CrossReady THEN
    B_Pulse := FALSE;
    IF B_Reset THEN
        B_Captured := FALSE;
        B_Code := 0;
    ELSIF B_Arm AND (NOT B_Captured) THEN
        IF B_EventA AND (NOT B_PrevA) THEN
            B_Captured := TRUE;
            B_Code := 1;
            B_Pulse := TRUE;
        ELSIF B_EventB AND (NOT B_PrevB) THEN
            B_Captured := TRUE;
            B_Code := 2;
            B_Pulse := TRUE;
        END_IF;
    END_IF;
    B_PrevA := B_EventA;
    B_PrevB := B_EventB;
ELSE
    B_Captured := FALSE;
    B_Code := 0;
    B_Pulse := FALSE;
END_IF;

END_FUNCTION_BLOCK
