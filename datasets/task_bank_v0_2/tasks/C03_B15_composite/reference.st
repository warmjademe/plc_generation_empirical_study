FUNCTION_BLOCK C03_B15_composite
VAR_INPUT
    A_Temperature : REAL;
    A_Setpoint : REAL;
    A_Enable : BOOL;
    A_SafetyTrip : BOOL;
    B_RunRequest : BOOL;
    B_TankLevelOK : BOOL;
    B_ValveFeedbackOpen : BOOL;
    B_PumpFeedback : BOOL;
    B_Stop : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Heat : BOOL;
    A_Cool : BOOL;
    B_ValveCommand : BOOL;
    B_PumpCommand : BOOL;
    B_InterlockAlarm : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR

A_Heat := FALSE;
A_Cool := FALSE;
IF A_Enable AND (NOT A_SafetyTrip) THEN
    IF A_Temperature < (A_Setpoint - 1.0) THEN
        A_Heat := TRUE;
    ELSIF A_Temperature > (A_Setpoint + 1.0) THEN
        A_Cool := TRUE;
    END_IF;
END_IF;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Heat THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

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
