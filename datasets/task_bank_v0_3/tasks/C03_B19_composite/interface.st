FUNCTION_BLOCK C03_B19_composite
VAR_INPUT
    A_HeatRequest : BOOL;
    A_Stop : BOOL;
    A_GuardClosed : BOOL;
    A_DamperOpen : BOOL;
    A_AirflowOK : BOOL;
    A_Reset : BOOL;
    B_RunRequest : BOOL;
    B_TankLevelOK : BOOL;
    B_ValveFeedbackOpen : BOOL;
    B_PumpFeedback : BOOL;
    B_Stop : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_DamperCommand : BOOL;
    A_FanCommand : BOOL;
    A_HeaterCommand : BOOL;
    A_Fault : BOOL;
    A_State : INT;
    B_ValveCommand : BOOL;
    B_PumpCommand : BOOL;
    B_InterlockAlarm : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
