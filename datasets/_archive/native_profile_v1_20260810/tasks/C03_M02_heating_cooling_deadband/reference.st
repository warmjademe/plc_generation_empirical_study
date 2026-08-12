FUNCTION_BLOCK C03_M02_heating_cooling_deadband
VAR_INPUT
    Temperature : REAL;
    Setpoint : REAL;
    Enable : BOOL;
    SafetyTrip : BOOL;
END_VAR
VAR_OUTPUT
    Heat : BOOL;
    Cool : BOOL;
END_VAR

Heat := FALSE;
Cool := FALSE;
IF Enable AND (NOT SafetyTrip) THEN
    IF Temperature < (Setpoint - 1.0) THEN
        Heat := TRUE;
    ELSIF Temperature > (Setpoint + 1.0) THEN
        Cool := TRUE;
    END_IF;
END_IF;

END_FUNCTION_BLOCK
