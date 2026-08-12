FUNCTION_BLOCK C03_B02_composite
VAR_INPUT
    A_RunRequest : BOOL;
    A_Stop : BOOL;
    A_C1Clear : BOOL;
    A_C2Clear : BOOL;
    A_C3Clear : BOOL;
    A_C2Available : BOOL;
    A_C3Available : BOOL;
    B_RunRequest : BOOL;
    B_TankLevelOK : BOOL;
    B_ValveFeedbackOpen : BOOL;
    B_PumpFeedback : BOOL;
    B_Stop : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_C1Run : BOOL;
    A_C2Run : BOOL;
    A_C3Run : BOOL;
    A_Blocked : BOOL;
    B_ValveCommand : BOOL;
    B_PumpCommand : BOOL;
    B_InterlockAlarm : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR

A_C3Run := A_RunRequest AND A_C3Available AND A_C3Clear AND (NOT A_Stop);
A_C2Run := A_C3Run AND A_C2Available AND A_C2Clear;
A_C1Run := A_C2Run AND A_C1Clear;
A_Blocked := A_RunRequest AND ((NOT A_C1Clear) OR (NOT A_C2Clear) OR (NOT A_C3Clear)
           OR (NOT A_C2Available) OR (NOT A_C3Available));

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_C1Run THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := FALSE;

IF SubsystemBEnable AND CrossReady THEN
    B_ValveCommand := B_RunRequest AND B_TankLevelOK AND (NOT B_Stop);
    B_PumpCommand := B_ValveCommand AND B_ValveFeedbackOpen;
    B_InterlockAlarm := B_PumpFeedback AND (NOT B_ValveFeedbackOpen);
ELSE
    B_ValveCommand := FALSE;
    B_PumpCommand := FALSE;
    B_InterlockAlarm := FALSE;
END_IF;

END_FUNCTION_BLOCK
