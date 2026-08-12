FUNCTION_BLOCK C06_M01_configurable_batch_counter
VAR_INPUT
    Item : BOOL;
    Reset : BOOL;
    Target : INT;
    Enable : BOOL;
END_VAR
VAR_OUTPUT
    Count : INT;
    BatchDone : BOOL;
    Accepted : BOOL;
END_VAR
END_FUNCTION_BLOCK
