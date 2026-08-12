FUNCTION_BLOCK C03_B09_composite
VAR_INPUT
    A_RunRequest : BOOL;
    A_TankLevelOK : BOOL;
    A_ValveFeedbackOpen : BOOL;
    A_PumpFeedback : BOOL;
    A_Stop : BOOL;
    B_RunRequest : BOOL;
    B_Stop : BOOL;
    B_C1Clear : BOOL;
    B_C2Clear : BOOL;
    B_C3Clear : BOOL;
    B_C2Available : BOOL;
    B_C3Available : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_ValveCommand : BOOL;
    A_PumpCommand : BOOL;
    A_InterlockAlarm : BOOL;
    B_C1Run : BOOL;
    B_C2Run : BOOL;
    B_C3Run : BOOL;
    B_Blocked : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR

A_ValveCommand := A_RunRequest AND A_TankLevelOK AND (NOT A_Stop);
A_PumpCommand := A_ValveCommand AND A_ValveFeedbackOpen;
A_InterlockAlarm := A_PumpFeedback AND (NOT A_ValveFeedbackOpen);

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_ValveCommand THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := FALSE;

IF SubsystemBEnable AND CrossReady THEN
    B_C3Run := B_RunRequest AND B_C3Available AND B_C3Clear AND (NOT B_Stop);
    B_C2Run := B_C3Run AND B_C2Available AND B_C2Clear;
    B_C1Run := B_C2Run AND B_C1Clear;
    B_Blocked := B_RunRequest AND ((NOT B_C1Clear) OR (NOT B_C2Clear) OR (NOT B_C3Clear)
               OR (NOT B_C2Available) OR (NOT B_C3Available));
ELSE
    B_C1Run := FALSE;
    B_C2Run := FALSE;
    B_C3Run := FALSE;
    B_Blocked := FALSE;
END_IF;

END_FUNCTION_BLOCK
