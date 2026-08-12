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
    B_RobotEnable := FALSE;
    B_ConveyorEnable := FALSE;
    B_ManualEnable := FALSE;
    B_Conflict := (B_RobotRequest AND B_ConveyorRequest)
                OR (B_RobotRequest AND B_ManualRequest AND B_ManualKey)
                OR (B_ConveyorRequest AND B_ManualRequest AND B_ManualKey);

    IF B_GuardClosed AND B_EStopOK THEN
        IF B_ManualRequest AND B_ManualKey THEN
            B_ManualEnable := TRUE;
        ELSIF B_RobotRequest THEN
            B_RobotEnable := TRUE;
        ELSIF B_ConveyorRequest THEN
            B_ConveyorEnable := TRUE;
        END_IF;
    END_IF;
ELSE
    B_RobotEnable := FALSE;
    B_ConveyorEnable := FALSE;
    B_ManualEnable := FALSE;
    B_Conflict := FALSE;
END_IF;

END_FUNCTION_BLOCK
