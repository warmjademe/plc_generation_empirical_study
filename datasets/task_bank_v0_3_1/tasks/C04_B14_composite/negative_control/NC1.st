FUNCTION_BLOCK C04_B14_composite
VAR_INPUT
    A_Button : BOOL;
    A_Enable : BOOL;
    A_Reset : BOOL;
    B_EventA : BOOL;
    B_EventB : BOOL;
    B_Arm : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_State : BOOL;
    A_AcceptedPulse : BOOL;
    B_Captured : BOOL;
    B_Code : INT;
    B_Pulse : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PrevButton : BOOL := FALSE;
    B_PrevA : BOOL := FALSE;
    B_PrevB : BOOL := FALSE;
END_VAR

A_AcceptedPulse := FALSE;
IF A_Reset THEN
    A_State := FALSE;
ELSIF A_Enable AND A_Button AND (NOT A_PrevButton) THEN
    A_State := NOT A_State;
    A_AcceptedPulse := TRUE;
END_IF;
A_PrevButton := A_Button;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_State THEN
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
