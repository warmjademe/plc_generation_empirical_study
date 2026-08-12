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
VAR
    PrevA : BOOL;
    PrevB : BOOL;
END_VAR

PulseA := FALSE;
PulseB := FALSE;
IF Reset AND (NOT EventA) AND (NOT EventB) THEN
    Count := 0;
    Locked := FALSE;
    LastSource := 0;
ELSIF MaxCount <= 0 THEN
    Locked := FALSE;
ELSIF Qualify AND (NOT Inhibit) AND (NOT Locked) THEN
    IF EventA AND (NOT PrevA) THEN
        PulseA := TRUE;
        Count := Count + 1;
        LastSource := 1;
    ELSIF EventB AND (NOT PrevB) THEN
        PulseB := TRUE;
        Count := Count + 1;
        LastSource := 2;
    END_IF;
    IF Count >= MaxCount THEN Count := MaxCount; Locked := TRUE; END_IF;
END_IF;
PrevA := EventA;
PrevB := EventB;

END_FUNCTION_BLOCK
