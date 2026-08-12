FUNCTION_BLOCK C06_H02_inspection_window_lockout
VAR_INPUT
    Inspected : BOOL;
    Rejected : BOOL;
    Reset : BOOL;
    WindowSize : INT;
    RejectLimit : INT;
END_VAR
VAR_OUTPUT
    WindowCount : INT;
    RejectCount : INT;
    LockedOut : BOOL;
    WindowComplete : BOOL;
END_VAR
END_FUNCTION_BLOCK
