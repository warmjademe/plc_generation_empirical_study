FUNCTION_BLOCK C07_M02_temperature_hysteresis
VAR_INPUT
    Temperature : REAL;
    LowThreshold : REAL;
    HighThreshold : REAL;
    Enable : BOOL;
END_VAR
VAR_OUTPUT
    Heater : BOOL;
    ConfigError : BOOL;
END_VAR
END_FUNCTION_BLOCK
