FUNCTION_BLOCK C03_B07_composite
VAR_INPUT
    A_RobotRequest : BOOL;
    A_ConveyorRequest : BOOL;
    A_ManualRequest : BOOL;
    A_GuardClosed : BOOL;
    A_EStopOK : BOOL;
    A_ManualKey : BOOL;
    B_Temperature : REAL;
    B_Setpoint : REAL;
    B_Enable : BOOL;
    B_SafetyTrip : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_RobotEnable : BOOL;
    A_ConveyorEnable : BOOL;
    A_ManualEnable : BOOL;
    A_Conflict : BOOL;
    B_Heat : BOOL;
    B_Cool : BOOL;
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
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

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
