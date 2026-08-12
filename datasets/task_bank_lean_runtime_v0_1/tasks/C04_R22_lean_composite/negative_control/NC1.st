FUNCTION_BLOCK C04_R22_lean_composite
VAR_INPUT
    A_EventA : BOOL;
    A_EventB : BOOL;
    A_Qualify : BOOL;
    A_Inhibit : BOOL;
    A_Reset : BOOL;
    A_MaxCount : INT;
    B_ChA : BOOL;
    B_ChB : BOOL;
    B_TestMode : BOOL;
    B_TestPermit : BOOL;
    B_ProcessRequest : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_PulseA : BOOL;
    A_PulseB : BOOL;
    A_Count : INT;
    A_Locked : BOOL;
    A_LastSource : INT;
    B_SafeEnable : BOOL;
    B_Disagree : BOOL;
    B_TestActive : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PrevA : BOOL;
    A_PrevB : BOOL;
END_VAR

A_PulseA := FALSE;
A_PulseB := FALSE;
IF A_Reset AND (NOT A_EventA) AND (NOT A_EventB) THEN
    A_Count := 0;
    A_Locked := FALSE;
    A_LastSource := 0;
ELSIF A_MaxCount <= 0 THEN
    A_Locked := TRUE;
ELSIF A_Qualify AND (NOT A_Inhibit) AND (NOT A_Locked) THEN
    IF A_EventA AND (NOT A_PrevA) THEN
        A_PulseA := TRUE;
        A_Count := A_Count + 1;
        A_LastSource := 1;
    ELSIF A_EventB AND (NOT A_PrevB) THEN
        A_PulseB := TRUE;
        A_Count := A_Count + 1;
        A_LastSource := 2;
    END_IF;
    IF A_Count >= A_MaxCount THEN A_Count := A_MaxCount; A_Locked := TRUE; END_IF;
END_IF;
A_PrevA := A_EventA;
A_PrevB := A_EventB;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_PulseA THEN
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
