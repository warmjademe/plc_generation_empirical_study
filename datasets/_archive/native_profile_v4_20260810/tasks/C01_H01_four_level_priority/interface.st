FUNCTION_BLOCK C01_H01_four_level_priority
VAR_INPUT
    Info : BOOL;
    Warning : BOOL;
    Trip : BOOL;
    Emergency : BOOL;
    Suppress : BOOL;
END_VAR
VAR_OUTPUT
    Active : BOOL;
    Level : INT;
END_VAR
END_FUNCTION_BLOCK
