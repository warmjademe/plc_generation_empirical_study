FUNCTION_BLOCK C04_H02_dual_event_priority_lockout
VAR_INPUT
    EventA : BOOL;
    EventB : BOOL;
    Arm : BOOL;
    Reset : BOOL;
END_VAR
VAR_OUTPUT
    Captured : BOOL;
    Code : INT;
    Pulse : BOOL;
END_VAR
VAR
    PrevA : BOOL := FALSE;
    PrevB : BOOL := FALSE;
END_VAR

Pulse := FALSE;
IF Reset THEN
    Captured := FALSE;
    Code := 0;
ELSIF Arm AND (NOT Captured) THEN
    IF EventA AND (NOT PrevA) THEN
        Captured := FALSE;
        Code := 1;
        Pulse := TRUE;
    ELSIF EventB AND (NOT PrevB) THEN
        Captured := TRUE;
        Code := 2;
        Pulse := TRUE;
    END_IF;
END_IF;
PrevA := EventA;
PrevB := EventB;

END_FUNCTION_BLOCK
