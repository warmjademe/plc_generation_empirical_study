FUNCTION_BLOCK C05_H01_two_stage_startup
VAR_INPUT
    Start : BOOL;
    Stop : BOOL;
    Permit : BOOL;
    Stage1Feedback : BOOL;
END_VAR
VAR_OUTPUT
    Stage1 : BOOL;
    Stage2 : BOOL;
    Fault : BOOL;
END_VAR
END_FUNCTION_BLOCK
