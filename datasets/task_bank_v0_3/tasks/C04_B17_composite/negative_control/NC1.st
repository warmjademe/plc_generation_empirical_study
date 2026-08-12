FUNCTION_BLOCK C04_B17_composite
VAR_INPUT
    A_EventA : BOOL;
    A_EventB : BOOL;
    A_Qualify : BOOL;
    A_Inhibit : BOOL;
    A_Reset : BOOL;
    A_MaxCount : INT;
    B_Event : BOOL;
    B_Qualify : BOOL;
    B_Reset : BOOL;
    B_MaxCount : INT;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_PulseA : BOOL;
    A_PulseB : BOOL;
    A_Count : INT;
    A_Locked : BOOL;
    A_LastSource : INT;
    B_Count : INT;
    B_AcceptedPulse : BOOL;
    B_AtLimit : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PrevA : BOOL;
    A_PrevB : BOOL;
    B_PrevEvent : BOOL := FALSE;
END_VAR

A_PulseA := FALSE;
A_PulseB := FALSE;
IF A_Reset AND (NOT A_EventA) AND (NOT A_EventB) THEN
    A_Count := 0;
    A_Locked := FALSE;
    A_LastSource := 0;
ELSIF A_MaxCount <= 0 THEN
    A_Locked := FALSE;
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
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

IF SubsystemBEnable AND CrossReady THEN
    B_AcceptedPulse := FALSE;
    IF B_Reset THEN
        B_Count := 0;
    ELSIF B_Event AND (NOT B_PrevEvent) AND B_Qualify AND (B_Count < B_MaxCount) THEN
        B_Count := B_Count + 1;
        B_AcceptedPulse := TRUE;
    END_IF;
    B_AtLimit := B_Count >= B_MaxCount;
    B_PrevEvent := B_Event;
ELSE
    B_Count := 0;
    B_AcceptedPulse := FALSE;
    B_AtLimit := FALSE;
END_IF;

END_FUNCTION_BLOCK
