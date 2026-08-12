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
END_FUNCTION_BLOCK
