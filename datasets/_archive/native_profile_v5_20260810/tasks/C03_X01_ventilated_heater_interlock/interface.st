FUNCTION_BLOCK C03_X01_ventilated_heater_interlock
VAR_INPUT
    HeatRequest : BOOL;
    Stop : BOOL;
    GuardClosed : BOOL;
    DamperOpen : BOOL;
    AirflowOK : BOOL;
    Reset : BOOL;
END_VAR
VAR_OUTPUT
    DamperCommand : BOOL;
    FanCommand : BOOL;
    HeaterCommand : BOOL;
    Fault : BOOL;
    State : INT;
END_VAR
END_FUNCTION_BLOCK
