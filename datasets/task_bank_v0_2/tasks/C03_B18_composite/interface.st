FUNCTION_BLOCK C03_B18_composite
VAR_INPUT
    A_HeatRequest : BOOL;
    A_Stop : BOOL;
    A_GuardClosed : BOOL;
    A_DamperOpen : BOOL;
    A_AirflowOK : BOOL;
    A_Reset : BOOL;
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
    A_DamperCommand : BOOL;
    A_FanCommand : BOOL;
    A_HeaterCommand : BOOL;
    A_Fault : BOOL;
    A_State : INT;
    B_RobotEnable : BOOL;
    B_ConveyorEnable : BOOL;
    B_ManualEnable : BOOL;
    B_Conflict : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
