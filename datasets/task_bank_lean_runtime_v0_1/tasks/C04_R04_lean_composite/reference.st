FUNCTION_BLOCK C04_R04_lean_composite
VAR_INPUT
    A_Event : BOOL;
    A_Qualify : BOOL;
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
    A_Count : INT;
    A_AcceptedPulse : BOOL;
    A_AtLimit : BOOL;
    B_Command : BOOL;
    B_Blocked : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PrevEvent : BOOL := FALSE;
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
