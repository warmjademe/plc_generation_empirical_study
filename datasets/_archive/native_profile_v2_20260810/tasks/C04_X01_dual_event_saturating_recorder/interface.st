FUNCTION_BLOCK C04_X01_dual_event_saturating_recorder
VAR_INPUT
    EventA : BOOL;
    EventB : BOOL;
    Qualify : BOOL;
    Inhibit : BOOL;
    Reset : BOOL;
    MaxCount : INT;
END_VAR
VAR_OUTPUT
    PulseA : BOOL;
    PulseB : BOOL;
    Count : INT;
    Locked : BOOL;
    LastSource : INT;
END_VAR
END_FUNCTION_BLOCK
