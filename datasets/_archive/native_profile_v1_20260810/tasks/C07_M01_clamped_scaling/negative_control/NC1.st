FUNCTION_BLOCK C07_M01_clamped_scaling
VAR_INPUT
    Raw : INT;
END_VAR
VAR_OUTPUT
    Engineering : REAL;
    UnderRange : BOOL;
    OverRange : BOOL;
END_VAR

UnderRange := FALSE;
OverRange := FALSE;
IF Raw < 0 THEN
    Engineering := 0.0;
    UnderRange := FALSE;
ELSIF Raw > 4095 THEN
    Engineering := 10.0;
    OverRange := TRUE;
ELSE
    Engineering := INT_TO_REAL(Raw) * 10.0 / 4095.0;
END_IF;

END_FUNCTION_BLOCK
