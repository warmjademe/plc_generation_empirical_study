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
END_FUNCTION_BLOCK
