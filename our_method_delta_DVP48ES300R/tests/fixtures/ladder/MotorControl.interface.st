FUNCTION_BLOCK MotorControl
VAR_INPUT
    StartButton : BOOL;
    StopButton : BOOL;
    Permit : BOOL;
END_VAR
VAR_OUTPUT
    MotorRun : BOOL;
    Ready : BOOL;
END_VAR
END_FUNCTION_BLOCK
