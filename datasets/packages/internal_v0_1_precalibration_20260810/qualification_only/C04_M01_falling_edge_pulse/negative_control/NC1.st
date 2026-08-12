FUNCTION_BLOCK C04_M01_falling_edge_pulse
VAR_INPUT
    Signal : BOOL;
    Arm : BOOL;
END_VAR
VAR_OUTPUT
    Pulse : BOOL;
    Armed : BOOL;
END_VAR
VAR
    PrevSignal : BOOL := TRUE;
END_VAR

Pulse := Arm AND (NOT Signal) AND PrevSignal;
Armed := Arm;
PrevSignal := Signal;

END_FUNCTION_BLOCK
