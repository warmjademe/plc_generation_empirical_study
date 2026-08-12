FUNCTION_BLOCK C08_H01_pause_resume_abort_sequence
VAR_INPUT
    Start : BOOL;
    Advance : BOOL;
    Pause : BOOL;
    Resume : BOOL;
    Abort : BOOL;
    Reset : BOOL;
END_VAR
VAR_OUTPUT
    Step1 : BOOL;
    Step2 : BOOL;
    Paused : BOOL;
    Aborted : BOOL;
    State : INT;
END_VAR
END_FUNCTION_BLOCK
