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
END_FUNCTION_BLOCK
