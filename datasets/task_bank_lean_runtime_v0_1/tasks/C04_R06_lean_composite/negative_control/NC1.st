FUNCTION_BLOCK C04_R06_lean_composite
VAR_INPUT
    A_EventA : BOOL;
    A_EventB : BOOL;
    A_Arm : BOOL;
    A_Reset : BOOL;
    B_Info : BOOL;
    B_Warning : BOOL;
    B_Trip : BOOL;
    B_Emergency : BOOL;
    B_Suppress : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Captured : BOOL;
    A_Code : INT;
    A_Pulse : BOOL;
    B_Active : BOOL;
    B_Level : INT;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PrevA : BOOL := FALSE;
    A_PrevB : BOOL := FALSE;
END_VAR

A_Pulse := FALSE;
IF A_Reset THEN
    A_Captured := FALSE;
    A_Code := 0;
ELSIF A_Arm AND (NOT A_Captured) THEN
    IF A_EventA AND (NOT A_PrevA) THEN
        A_Captured := TRUE;
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
