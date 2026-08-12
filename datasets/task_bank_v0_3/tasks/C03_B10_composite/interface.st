FUNCTION_BLOCK C03_B10_composite
VAR_INPUT
    A_RunRequest : BOOL;
    A_TankLevelOK : BOOL;
    A_ValveFeedbackOpen : BOOL;
    A_PumpFeedback : BOOL;
    A_Stop : BOOL;
    B_RobotRequest : BOOL;
    B_ConveyorRequest : BOOL;
    B_ManualRequest : BOOL;
    B_GuardClosed : BOOL;
    B_EStopOK : BOOL;
    B_ManualKey : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_ValveCommand : BOOL;
    A_PumpCommand : BOOL;
    A_InterlockAlarm : BOOL;
    B_RobotEnable : BOOL;
    B_ConveyorEnable : BOOL;
    B_ManualEnable : BOOL;
    B_Conflict : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
