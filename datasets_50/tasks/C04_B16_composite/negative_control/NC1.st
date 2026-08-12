FUNCTION_BLOCK C04_B16_composite
VAR_INPUT
    A_Button : BOOL;
    A_Enable : BOOL;
    A_Reset : BOOL;
    B_EventA : BOOL;
    B_EventB : BOOL;
    B_Qualify : BOOL;
    B_Inhibit : BOOL;
    B_Reset : BOOL;
    B_MaxCount : INT;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_State : BOOL;
    A_AcceptedPulse : BOOL;
    B_PulseA : BOOL;
    B_PulseB : BOOL;
    B_Count : INT;
    B_Locked : BOOL;
    B_LastSource : INT;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PrevButton : BOOL := FALSE;
    B_PrevA : BOOL;
    B_PrevB : BOOL;
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
    B_PulseA := FALSE;
    B_PulseB := FALSE;
    IF B_Reset AND (NOT B_EventA) AND (NOT B_EventB) THEN
        B_Count := 0;
        B_Locked := FALSE;
        B_LastSource := 0;
    ELSIF B_MaxCount <= 0 THEN
        B_Locked := TRUE;
    ELSIF B_Qualify AND (NOT B_Inhibit) AND (NOT B_Locked) THEN
        IF B_EventA AND (NOT B_PrevA) THEN
            B_PulseA := TRUE;
            B_Count := B_Count + 1;
            B_LastSource := 1;
        ELSIF B_EventB AND (NOT B_PrevB) THEN
            B_PulseB := TRUE;
            B_Count := B_Count + 1;
            B_LastSource := 2;
        END_IF;
        IF B_Count >= B_MaxCount THEN B_Count := B_MaxCount; B_Locked := TRUE; END_IF;
    END_IF;
    B_PrevA := B_EventA;
    B_PrevB := B_EventB;
ELSE
    B_PulseA := FALSE;
    B_PulseB := FALSE;
    B_Count := 0;
    B_Locked := FALSE;
    B_LastSource := 0;
END_IF;

END_FUNCTION_BLOCK
