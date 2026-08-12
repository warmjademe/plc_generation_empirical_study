FUNCTION_BLOCK C04_B07_composite
VAR_INPUT
    A_EventA : BOOL;
    A_EventB : BOOL;
    A_Arm : BOOL;
    A_Reset : BOOL;
    B_Button : BOOL;
    B_Enable : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Captured : BOOL;
    A_Code : INT;
    A_Pulse : BOOL;
    B_State : BOOL;
    B_AcceptedPulse : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PrevA : BOOL := FALSE;
    A_PrevB : BOOL := FALSE;
    B_PrevButton : BOOL := FALSE;
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
        B_State := FALSE;
    ELSIF B_Enable AND B_Button AND (NOT B_PrevButton) THEN
        B_State := NOT B_State;
        B_AcceptedPulse := TRUE;
    END_IF;
    B_PrevButton := B_Button;
ELSE
    B_State := FALSE;
    B_AcceptedPulse := FALSE;
END_IF;

END_FUNCTION_BLOCK
