FUNCTION_BLOCK C03_H01_conveyor_cascade_interlock
VAR_INPUT
    RunRequest : BOOL;
    Stop : BOOL;
    C1Clear : BOOL;
    C2Clear : BOOL;
    C3Clear : BOOL;
    C2Available : BOOL;
    C3Available : BOOL;
END_VAR
VAR_OUTPUT
    C1Run : BOOL;
    C2Run : BOOL;
    C3Run : BOOL;
    Blocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
