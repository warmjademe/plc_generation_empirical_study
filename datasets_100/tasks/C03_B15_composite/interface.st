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
END_FUNCTION_BLOCK
