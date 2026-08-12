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
VAR
    PrevInspected : BOOL := FALSE;
END_VAR

WindowComplete := FALSE;
IF Reset THEN
    WindowCount := 0;
    RejectCount := 0;
    LockedOut := FALSE;
ELSIF (NOT LockedOut) AND Inspected AND (NOT PrevInspected) THEN
    WindowCount := WindowCount + 1;
    IF Rejected THEN
        RejectCount := RejectCount + 1;
    END_IF;
    IF WindowCount >= WindowSize THEN
        IF RejectCount > RejectLimit THEN
            LockedOut := TRUE;
        END_IF;
        WindowCount := 0;
        RejectCount := 0;
        WindowComplete := TRUE;
    END_IF;
END_IF;
PrevInspected := Inspected;

END_FUNCTION_BLOCK
