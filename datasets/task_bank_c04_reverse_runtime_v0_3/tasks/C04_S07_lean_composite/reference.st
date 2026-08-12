FUNCTION_BLOCK C04_S07_lean_composite
VAR_INPUT
    A_ChA : BOOL;
    A_ChB : BOOL;
    A_TestMode : BOOL;
    A_TestPermit : BOOL;
    A_ProcessRequest : BOOL;
    B_EventA : BOOL;
    B_EventB : BOOL;
    B_Arm : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_SafeEnable : BOOL;
    A_Disagree : BOOL;
    A_TestActive : BOOL;
    B_Captured : BOOL;
    B_Code : INT;
    B_Pulse : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    B_PrevA : BOOL := FALSE;
    B_PrevB : BOOL := FALSE;
END_VAR

A_Disagree := A_ChA <> A_ChB;
A_TestActive := A_TestMode AND A_TestPermit;
IF A_TestMode THEN
    A_SafeEnable := A_ProcessRequest AND A_TestPermit AND A_ChA;
ELSE
    A_SafeEnable := A_ProcessRequest AND A_ChA AND A_ChB;
END_IF;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_SafeEnable THEN
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
