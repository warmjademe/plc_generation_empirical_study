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
    B_C3Run := B_RunRequest AND B_C3Available AND B_C3Clear AND (NOT B_Stop);
    B_C2Run := B_C3Run AND B_C2Available AND B_C2Clear;
    B_C1Run := B_C2Run AND B_C1Clear;
    B_Blocked := B_RunRequest AND ((NOT B_C1Clear) OR (NOT B_C2Clear) OR (NOT B_C3Clear)
               OR (NOT B_C2Available) OR (NOT B_C3Available));
ELSE
    B_C1Run := FALSE;
    B_C2Run := FALSE;
    B_C3Run := FALSE;
    B_Blocked := FALSE;
END_IF;

END_FUNCTION_BLOCK
