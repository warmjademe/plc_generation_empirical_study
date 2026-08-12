FUNCTION_BLOCK C08_E01_two_step_cycle
VAR_INPUT
    Start : BOOL;
    Step1Done : BOOL;
    Step2Done : BOOL;
    Reset : BOOL;
END_VAR
VAR_OUTPUT
    Step1 : BOOL;
    Step2 : BOOL;
    Complete : BOOL;
    State : INT;
END_VAR
END_FUNCTION_BLOCK
