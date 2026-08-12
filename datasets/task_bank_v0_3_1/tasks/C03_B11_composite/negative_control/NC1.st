FUNCTION_BLOCK C03_B11_composite
VAR_INPUT
    A_RunRequest : BOOL;
    A_TankLevelOK : BOOL;
    A_ValveFeedbackOpen : BOOL;
    A_PumpFeedback : BOOL;
    A_Stop : BOOL;
    B_Temperature : REAL;
    B_Setpoint : REAL;
    B_Enable : BOOL;
    B_SafetyTrip : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_ValveCommand : BOOL;
    A_PumpCommand : BOOL;
    A_InterlockAlarm : BOOL;
    B_Heat : BOOL;
    B_Cool : BOOL;
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
    B_Heat := FALSE;
    B_Cool := FALSE;
    IF B_Enable AND (NOT B_SafetyTrip) THEN
        IF B_Temperature < (B_Setpoint - 1.0) THEN
            B_Heat := TRUE;
        ELSIF B_Temperature > (B_Setpoint + 1.0) THEN
            B_Cool := TRUE;
        END_IF;
    END_IF;
ELSE
    B_Heat := FALSE;
    B_Cool := FALSE;
END_IF;

END_FUNCTION_BLOCK
