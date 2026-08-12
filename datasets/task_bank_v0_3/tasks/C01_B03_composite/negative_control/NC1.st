FUNCTION_BLOCK C01_B03_composite
VAR_INPUT
    A_Info : BOOL;
    A_Warning : BOOL;
    A_Trip : BOOL;
    A_Emergency : BOOL;
    A_Suppress : BOOL;
    B_AutoMode : BOOL;
    B_AutoDemand : BOOL;
    B_ManualDemand : BOOL;
    B_SafetyOK : BOOL;
    B_Inhibit : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Active : BOOL;
    A_Level : INT;
    B_Command : BOOL;
    B_Blocked : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR

IF A_Emergency THEN
    A_Level := 4;
    A_Active := FALSE;
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
    B_Command := ((B_AutoMode AND B_AutoDemand) OR ((NOT B_AutoMode) AND B_ManualDemand))
               AND B_SafetyOK AND (NOT B_Inhibit);
    B_Blocked := ((B_AutoMode AND B_AutoDemand) OR ((NOT B_AutoMode) AND B_ManualDemand))
               AND ((NOT B_SafetyOK) OR B_Inhibit);
ELSE
    B_Command := FALSE;
    B_Blocked := FALSE;
END_IF;

END_FUNCTION_BLOCK
