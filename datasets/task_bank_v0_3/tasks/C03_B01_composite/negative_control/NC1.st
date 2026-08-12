FUNCTION_BLOCK C03_B01_composite
VAR_INPUT
    A_RunRequest : BOOL;
    A_Stop : BOOL;
    A_C1Clear : BOOL;
    A_C2Clear : BOOL;
    A_C3Clear : BOOL;
    A_C2Available : BOOL;
    A_C3Available : BOOL;
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
    A_C1Run : BOOL;
    A_C2Run : BOOL;
    A_C3Run : BOOL;
    A_Blocked : BOOL;
    B_RobotEnable : BOOL;
    B_ConveyorEnable : BOOL;
    B_ManualEnable : BOOL;
    B_Conflict : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR

A_C3Run := A_RunRequest AND A_C3Available AND A_C3Clear AND (NOT A_Stop);
A_C2Run := A_C3Run AND A_C2Available AND A_C2Clear;
A_C1Run := A_C2Run AND A_C1Clear;
A_Blocked := A_RunRequest AND ((NOT A_C1Clear) OR (NOT A_C2Clear) OR (NOT A_C3Clear)
           OR (NOT A_C2Available) OR (NOT A_C3Available));

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_C1Run THEN
    CrossReady := FALSE;
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
