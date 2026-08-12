FUNCTION_BLOCK C03_B04_composite
VAR_INPUT
    A_RunRequest : BOOL;
    A_Stop : BOOL;
    A_C1Clear : BOOL;
    A_C2Clear : BOOL;
    A_C3Clear : BOOL;
    A_C2Available : BOOL;
    A_C3Available : BOOL;
    B_HeatRequest : BOOL;
    B_Stop : BOOL;
    B_GuardClosed : BOOL;
    B_DamperOpen : BOOL;
    B_AirflowOK : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_C1Run : BOOL;
    A_C2Run : BOOL;
    A_C3Run : BOOL;
    A_Blocked : BOOL;
    B_DamperCommand : BOOL;
    B_FanCommand : BOOL;
    B_HeaterCommand : BOOL;
    B_Fault : BOOL;
    B_State : INT;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
