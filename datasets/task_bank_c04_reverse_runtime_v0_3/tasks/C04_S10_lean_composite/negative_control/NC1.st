FUNCTION_BLOCK C04_S10_lean_composite
VAR_INPUT
    A_ChA : BOOL;
    A_ChB : BOOL;
    A_TestMode : BOOL;
    A_TestPermit : BOOL;
    A_ProcessRequest : BOOL;
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
    A_SafeEnable : BOOL;
    A_Disagree : BOOL;
    A_TestActive : BOOL;
    B_PulseA : BOOL;
    B_PulseB : BOOL;
    B_Count : INT;
    B_Locked : BOOL;
    B_LastSource : INT;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    B_PrevA : BOOL;
    B_PrevB : BOOL;
END_VAR

A_Disagree := A_ChA <> A_ChB;
A_TestActive := A_TestMode AND A_TestPermit;
IF A_TestMode THEN
    A_SafeEnable := A_ProcessRequest AND A_TestPermit AND A_ChA;
ELSE
    A_SafeEnable := A_ProcessRequest AND A_ChA AND A_ChB;
END_IF;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_SafeEnable THEN
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
