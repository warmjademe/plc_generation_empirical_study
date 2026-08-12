FUNCTION_BLOCK C04_B18_composite
VAR_INPUT
    A_EventA : BOOL;
    A_EventB : BOOL;
    A_Qualify : BOOL;
    A_Inhibit : BOOL;
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
    A_PulseA : BOOL;
    A_PulseB : BOOL;
    A_Count : INT;
    A_Locked : BOOL;
    A_LastSource : INT;
    B_Captured : BOOL;
    B_Code : INT;
    B_Pulse : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PrevA : BOOL;
    A_PrevB : BOOL;
    B_PrevA : BOOL := FALSE;
    B_PrevB : BOOL := FALSE;
END_VAR

A_PulseA := FALSE;
A_PulseB := FALSE;
IF A_Reset AND (NOT A_EventA) AND (NOT A_EventB) THEN
    A_Count := 0;
    A_Locked := FALSE;
    A_LastSource := 0;
ELSIF A_MaxCount <= 0 THEN
    A_Locked := TRUE;
ELSIF A_Qualify AND (NOT A_Inhibit) AND (NOT A_Locked) THEN
    IF A_EventA AND (NOT A_PrevA) THEN
        A_PulseA := TRUE;
        A_Count := A_Count + 1;
        A_LastSource := 1;
    ELSIF A_EventB AND (NOT A_PrevB) THEN
        A_PulseB := TRUE;
        A_Count := A_Count + 1;
        A_LastSource := 2;
    END_IF;
    IF A_Count >= A_MaxCount THEN A_Count := A_MaxCount; A_Locked := TRUE; END_IF;
END_IF;
A_PrevA := A_EventA;
A_PrevB := A_EventB;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_PulseA THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := FALSE;

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
