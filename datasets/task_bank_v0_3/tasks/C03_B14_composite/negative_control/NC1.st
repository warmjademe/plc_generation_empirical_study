FUNCTION_BLOCK C03_B14_composite
VAR_INPUT
    A_Temperature : REAL;
    A_Setpoint : REAL;
    A_Enable : BOOL;
    A_SafetyTrip : BOOL;
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
    A_Heat : BOOL;
    A_Cool : BOOL;
    B_RobotEnable : BOOL;
    B_ConveyorEnable : BOOL;
    B_ManualEnable : BOOL;
    B_Conflict : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR

A_Heat := FALSE;
A_Cool := FALSE;
IF A_Enable AND (NOT A_SafetyTrip) THEN
    IF A_Temperature < (A_Setpoint - 1.0) THEN
        A_Heat := FALSE;
    ELSIF A_Temperature > (A_Setpoint + 1.0) THEN
        A_Cool := TRUE;
    END_IF;
END_IF;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Heat THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

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
