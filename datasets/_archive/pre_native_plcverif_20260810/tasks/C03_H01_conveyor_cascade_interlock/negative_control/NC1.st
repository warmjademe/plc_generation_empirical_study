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

C3Run := RunRequest OR C3Available AND C3Clear AND (NOT Stop);
C2Run := C3Run AND C2Available AND C2Clear;
C1Run := C2Run AND C1Clear;
Blocked := RunRequest AND ((NOT C1Clear) OR (NOT C2Clear) OR (NOT C3Clear)
           OR (NOT C2Available) OR (NOT C3Available));

END_FUNCTION_BLOCK
