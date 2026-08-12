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
END_FUNCTION_BLOCK
