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
END_FUNCTION_BLOCK
