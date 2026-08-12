FUNCTION_BLOCK C03_H02_safety_zone_arbitration
VAR_INPUT
    RobotRequest : BOOL;
    ConveyorRequest : BOOL;
    ManualRequest : BOOL;
    GuardClosed : BOOL;
    EStopOK : BOOL;
    ManualKey : BOOL;
END_VAR
VAR_OUTPUT
    RobotEnable : BOOL;
    ConveyorEnable : BOOL;
    ManualEnable : BOOL;
    Conflict : BOOL;
END_VAR

RobotEnable := FALSE;
ConveyorEnable := FALSE;
ManualEnable := FALSE;
Conflict := (RobotRequest AND ConveyorRequest)
            OR (RobotRequest AND ManualRequest AND ManualKey)
            OR (ConveyorRequest AND ManualRequest AND ManualKey);

IF GuardClosed AND EStopOK THEN
    IF ManualRequest AND ManualKey THEN
        ManualEnable := FALSE;
    ELSIF RobotRequest THEN
        RobotEnable := TRUE;
    ELSIF ConveyorRequest THEN
        ConveyorEnable := TRUE;
    END_IF;
END_IF;

END_FUNCTION_BLOCK
