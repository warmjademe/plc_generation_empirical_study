FUNCTION_BLOCK C01_B01_composite
VAR_INPUT
    A_Info : BOOL;
    A_Warning : BOOL;
    A_Trip : BOOL;
    A_Emergency : BOOL;
    A_Suppress : BOOL;
    B_ChA : BOOL;
    B_ChB : BOOL;
    B_TestMode : BOOL;
    B_TestPermit : BOOL;
    B_ProcessRequest : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Active : BOOL;
    A_Level : INT;
    B_SafeEnable : BOOL;
    B_Disagree : BOOL;
    B_TestActive : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
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
    B_Disagree := B_ChA <> B_ChB;
    B_TestActive := B_TestMode AND B_TestPermit;
    IF B_TestMode THEN
        B_SafeEnable := B_ProcessRequest AND B_TestPermit AND B_ChA;
    ELSE
        B_SafeEnable := B_ProcessRequest AND B_ChA AND B_ChB;
    END_IF;
ELSE
    B_SafeEnable := FALSE;
    B_Disagree := FALSE;
    B_TestActive := FALSE;
END_IF;

END_FUNCTION_BLOCK
