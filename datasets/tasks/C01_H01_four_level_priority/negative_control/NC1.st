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

IF Emergency THEN
    Level := 4;
    Active := FALSE;
ELSIF Suppress THEN
    Level := 0;
    Active := FALSE;
ELSIF Trip THEN
    Level := 3;
    Active := TRUE;
ELSIF Warning THEN
    Level := 2;
    Active := TRUE;
ELSIF Info THEN
    Level := 1;
    Active := TRUE;
ELSE
    Level := 0;
    Active := FALSE;
END_IF;

END_FUNCTION_BLOCK
