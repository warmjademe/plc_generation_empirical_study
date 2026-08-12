FUNCTION_BLOCK C04_E01_rising_edge_pulse
VAR_INPUT
    Signal : BOOL;
END_VAR
VAR_OUTPUT
    Pulse : BOOL;
END_VAR
VAR
    PrevSignal : BOOL := TRUE;
END_VAR

Pulse := Signal AND (NOT PrevSignal);
PrevSignal := Signal;

END_FUNCTION_BLOCK
