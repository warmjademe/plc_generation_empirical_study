FUNCTION_BLOCK C04_R16_lean_composite
VAR_INPUT
    A_Button : BOOL;
    A_Enable : BOOL;
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
    A_State : BOOL;
    A_AcceptedPulse : BOOL;
    B_Active : BOOL;
    B_Level : INT;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PrevButton : BOOL := FALSE;
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
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

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
