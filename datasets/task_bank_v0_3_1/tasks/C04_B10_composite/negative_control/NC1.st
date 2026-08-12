FUNCTION_BLOCK C04_B10_composite
VAR_INPUT
    A_Signal : BOOL;
    A_Arm : BOOL;
    B_EventA : BOOL;
    B_EventB : BOOL;
    B_Arm : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Pulse : BOOL;
    A_Armed : BOOL;
    B_Captured : BOOL;
    B_Code : INT;
    B_Pulse : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PrevSignal : BOOL := FALSE;
    B_PrevA : BOOL := FALSE;
    B_PrevB : BOOL := FALSE;
END_VAR

A_Pulse := A_Arm AND (NOT A_Signal) AND A_PrevSignal;
A_Armed := A_Arm;
A_PrevSignal := A_Signal;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Pulse THEN
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
