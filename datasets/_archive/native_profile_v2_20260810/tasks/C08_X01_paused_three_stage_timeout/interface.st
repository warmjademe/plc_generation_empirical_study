FUNCTION_BLOCK C08_X01_paused_three_stage_timeout
VAR_INPUT
    Start : BOOL;
    Stage1Done : BOOL;
    Stage2Done : BOOL;
    Stage3Done : BOOL;
    Pause : BOOL;
    Abort : BOOL;
    Reset : BOOL;
END_VAR
VAR_OUTPUT
    Actuator1 : BOOL;
    Actuator2 : BOOL;
    Actuator3 : BOOL;
    Paused : BOOL;
    Complete : BOOL;
    Fault : BOOL;
    State : INT;
END_VAR
END_FUNCTION_BLOCK
