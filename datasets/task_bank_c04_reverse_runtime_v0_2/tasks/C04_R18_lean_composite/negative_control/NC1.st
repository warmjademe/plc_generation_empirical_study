FUNCTION_BLOCK C04_R18_lean_composite
VAR_INPUT
    A_AutoMode : BOOL;
    A_AutoDemand : BOOL;
    A_ManualDemand : BOOL;
    A_SafetyOK : BOOL;
    A_Inhibit : BOOL;
    B_Signal : BOOL;
    B_Arm : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Command : BOOL;
    A_Blocked : BOOL;
    B_Pulse : BOOL;
    B_Armed : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    B_PrevSignal : BOOL := FALSE;
END_VAR

A_Command := ((A_AutoMode AND A_AutoDemand) OR ((NOT A_AutoMode) AND A_ManualDemand))
           AND A_SafetyOK AND (NOT A_Inhibit);
A_Blocked := ((A_AutoMode AND A_AutoDemand) OR ((NOT A_AutoMode) AND A_ManualDemand))
           AND ((NOT A_SafetyOK) OR A_Inhibit);

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Command THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := FALSE;

IF SubsystemBEnable AND CrossReady THEN
    B_Pulse := B_Arm AND (NOT B_Signal) AND B_PrevSignal;
    B_Armed := B_Arm;
    B_PrevSignal := B_Signal;
ELSE
    B_Pulse := FALSE;
    B_Armed := FALSE;
END_IF;

END_FUNCTION_BLOCK
