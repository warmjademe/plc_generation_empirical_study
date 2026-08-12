FUNCTION_BLOCK C04_R03_lean_composite
VAR_INPUT
    A_Info : BOOL;
    A_Warning : BOOL;
    A_Trip : BOOL;
    A_Emergency : BOOL;
    A_Suppress : BOOL;
    B_Signal : BOOL;
    B_Arm : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Active : BOOL;
    A_Level : INT;
    B_Pulse : BOOL;
    B_Armed : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    B_PrevSignal : BOOL := FALSE;
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
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

IF SubsystemBEnable AND CrossReady THEN
    B_Pulse := B_Arm AND (NOT B_Signal) AND B_PrevSignal;
    B_Armed := B_Arm;
    B_PrevSignal := B_Signal;
ELSE
    B_Pulse := FALSE;
    B_Armed := FALSE;
END_IF;

END_FUNCTION_BLOCK
