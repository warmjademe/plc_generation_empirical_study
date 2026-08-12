FUNCTION_BLOCK C03_B05_composite
VAR_INPUT
    A_RobotRequest : BOOL;
    A_ConveyorRequest : BOOL;
    A_ManualRequest : BOOL;
    A_GuardClosed : BOOL;
    A_EStopOK : BOOL;
    A_ManualKey : BOOL;
    B_RunRequest : BOOL;
    B_Stop : BOOL;
    B_C1Clear : BOOL;
    B_C2Clear : BOOL;
    B_C3Clear : BOOL;
    B_C2Available : BOOL;
    B_C3Available : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_RobotEnable : BOOL;
    A_ConveyorEnable : BOOL;
    A_ManualEnable : BOOL;
    A_Conflict : BOOL;
    B_C1Run : BOOL;
    B_C2Run : BOOL;
    B_C3Run : BOOL;
    B_Blocked : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
