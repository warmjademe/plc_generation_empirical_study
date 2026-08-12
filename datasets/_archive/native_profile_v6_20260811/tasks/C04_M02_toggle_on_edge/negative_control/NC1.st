FUNCTION_BLOCK C04_M02_toggle_on_edge
VAR_INPUT
    Button : BOOL;
    Enable : BOOL;
    Reset : BOOL;
END_VAR
VAR_OUTPUT
    State : BOOL;
    AcceptedPulse : BOOL;
END_VAR
VAR
    PrevButton : BOOL := FALSE;
END_VAR

AcceptedPulse := FALSE;
IF Reset THEN
    State := FALSE;
ELSIF Enable AND Button AND (NOT PrevButton) THEN
    State := NOT State;
    AcceptedPulse := FALSE;
END_IF;
PrevButton := Button;

END_FUNCTION_BLOCK
