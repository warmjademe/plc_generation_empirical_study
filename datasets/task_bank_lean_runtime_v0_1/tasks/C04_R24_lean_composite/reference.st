FUNCTION_BLOCK C04_R24_lean_composite
VAR_INPUT
    A_EventA : BOOL;
    A_EventB : BOOL;
    A_Qualify : BOOL;
    A_Inhibit : BOOL;
    A_Reset : BOOL;
    A_MaxCount : INT;
    B_AutoMode : BOOL;
    B_AutoDemand : BOOL;
    B_ManualDemand : BOOL;
    B_SafetyOK : BOOL;
    B_Inhibit : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_PulseA : BOOL;
    A_PulseB : BOOL;
    A_Count : INT;
    A_Locked : BOOL;
    A_LastSource : INT;
    B_Command : BOOL;
    B_Blocked : BOOL;
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
