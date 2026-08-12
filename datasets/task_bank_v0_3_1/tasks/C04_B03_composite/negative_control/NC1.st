FUNCTION_BLOCK C04_B03_composite
VAR_INPUT
    A_Event : BOOL;
    A_Qualify : BOOL;
    A_Reset : BOOL;
    A_MaxCount : INT;
    B_Button : BOOL;
    B_Enable : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Count : INT;
    A_AcceptedPulse : BOOL;
    A_AtLimit : BOOL;
    B_State : BOOL;
    B_AcceptedPulse : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PrevEvent : BOOL := FALSE;
    B_PrevButton : BOOL := FALSE;
END_VAR

A_AcceptedPulse := FALSE;
IF A_Reset THEN
    A_Count := 0;
ELSIF A_Event AND (NOT A_PrevEvent) AND A_Qualify AND (A_Count < A_MaxCount) THEN
    A_Count := A_Count + 1;
    A_AcceptedPulse := TRUE;
END_IF;
A_AtLimit := A_Count >= A_MaxCount;
A_PrevEvent := A_Event;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_AcceptedPulse THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := FALSE;

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
