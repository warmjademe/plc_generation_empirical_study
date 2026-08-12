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
END_FUNCTION_BLOCK
