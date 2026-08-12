FUNCTION_BLOCK C05_X01_pre_lube_motor_lifecycle
VAR_INPUT
    Start : BOOL;
    Stop : BOOL;
    Permit : BOOL;
    OilPressure : BOOL;
    MotorFeedback : BOOL;
    Reset : BOOL;
END_VAR
VAR_OUTPUT
    LubePump : BOOL;
    MotorCommand : BOOL;
    Cooldown : BOOL;
    Fault : BOOL;
    State : INT;
END_VAR
END_FUNCTION_BLOCK
