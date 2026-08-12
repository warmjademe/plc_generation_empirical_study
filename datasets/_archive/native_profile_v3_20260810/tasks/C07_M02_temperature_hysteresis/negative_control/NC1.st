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

ConfigError := LowThreshold >= HighThreshold;
IF (NOT Enable) OR ConfigError THEN
    Heater := FALSE;
ELSIF Temperature <= LowThreshold THEN
    Heater := FALSE;
ELSIF Temperature >= HighThreshold THEN
    Heater := FALSE;
END_IF;

END_FUNCTION_BLOCK
