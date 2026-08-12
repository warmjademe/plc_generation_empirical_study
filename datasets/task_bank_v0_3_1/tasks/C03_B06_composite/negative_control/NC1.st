FUNCTION_BLOCK C03_B06_composite
VAR_INPUT
    A_RobotRequest : BOOL;
    A_ConveyorRequest : BOOL;
    A_ManualRequest : BOOL;
    A_GuardClosed : BOOL;
    A_EStopOK : BOOL;
    A_ManualKey : BOOL;
    B_RunRequest : BOOL;
    B_TankLevelOK : BOOL;
    B_ValveFeedbackOpen : BOOL;
    B_PumpFeedback : BOOL;
    B_Stop : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_RobotEnable : BOOL;
    A_ConveyorEnable : BOOL;
    A_ManualEnable : BOOL;
    A_Conflict : BOOL;
    B_ValveCommand : BOOL;
    B_PumpCommand : BOOL;
    B_InterlockAlarm : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR

A_RobotEnable := FALSE;
A_ConveyorEnable := FALSE;
A_ManualEnable := FALSE;
A_Conflict := (A_RobotRequest AND A_ConveyorRequest)
            OR (A_RobotRequest AND A_ManualRequest AND A_ManualKey)
            OR (A_ConveyorRequest AND A_ManualRequest AND A_ManualKey);

IF A_GuardClosed AND A_EStopOK THEN
    IF A_ManualRequest AND A_ManualKey THEN
        A_ManualEnable := TRUE;
    ELSIF A_RobotRequest THEN
        A_RobotEnable := TRUE;
    ELSIF A_ConveyorRequest THEN
        A_ConveyorEnable := TRUE;
    END_IF;
END_IF;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_RobotEnable THEN
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
