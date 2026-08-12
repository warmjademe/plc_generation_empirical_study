FUNCTION_BLOCK C04_B02_composite
VAR_INPUT
    A_Event : BOOL;
    A_Qualify : BOOL;
    A_Reset : BOOL;
    A_MaxCount : INT;
    B_Signal : BOOL;
    B_Arm : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Count : INT;
    A_AcceptedPulse : BOOL;
    A_AtLimit : BOOL;
    B_Pulse : BOOL;
    B_Armed : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PrevEvent : BOOL := FALSE;
    B_PrevSignal : BOOL := FALSE;
END_VAR

A_AcceptedPulse := FALSE;
IF A_Reset THEN
    A_Count := 0;
ELSIF A_Event AND (NOT A_PrevEvent) AND A_Qualify AND (A_Count < A_MaxCount) THEN
    A_Count := A_Count + 1;
    A_AcceptedPulse := FALSE;
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
    B_Pulse := B_Arm AND (NOT B_Signal) AND B_PrevSignal;
    B_Armed := B_Arm;
    B_PrevSignal := B_Signal;
ELSE
    B_Pulse := FALSE;
    B_Armed := FALSE;
END_IF;

END_FUNCTION_BLOCK
