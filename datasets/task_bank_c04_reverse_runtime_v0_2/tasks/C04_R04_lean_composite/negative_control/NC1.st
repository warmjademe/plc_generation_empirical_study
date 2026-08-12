FUNCTION_BLOCK C04_R04_lean_composite
VAR_INPUT
    A_Info : BOOL;
    A_Warning : BOOL;
    A_Trip : BOOL;
    A_Emergency : BOOL;
    A_Suppress : BOOL;
    B_Button : BOOL;
    B_Enable : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Active : BOOL;
    A_Level : INT;
    B_State : BOOL;
    B_AcceptedPulse : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    B_PrevButton : BOOL := FALSE;
END_VAR

IF A_Emergency THEN
    A_Level := 4;
    A_Active := TRUE;
ELSIF A_Suppress THEN
    A_Level := 0;
    A_Active := FALSE;
ELSIF A_Trip THEN
    A_Level := 3;
    A_Active := TRUE;
ELSIF A_Warning THEN
    A_Level := 2;
    A_Active := TRUE;
ELSIF A_Info THEN
    A_Level := 1;
    A_Active := TRUE;
ELSE
    A_Level := 0;
    A_Active := FALSE;
END_IF;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Active THEN
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
