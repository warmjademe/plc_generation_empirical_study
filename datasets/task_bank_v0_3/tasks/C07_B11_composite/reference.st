FUNCTION_BLOCK C07_B11_composite
VAR_INPUT
    A_Raw : INT;
    B_Temperature : REAL;
    B_LowThreshold : REAL;
    B_HighThreshold : REAL;
    B_Enable : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Engineering : REAL;
    A_UnderRange : BOOL;
    A_OverRange : BOOL;
    B_Heater : BOOL;
    B_ConfigError : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR

A_UnderRange := FALSE;
A_OverRange := FALSE;
IF A_Raw < 0 THEN
    A_Engineering := 0.0;
    A_UnderRange := TRUE;
ELSIF A_Raw > 4095 THEN
    A_Engineering := 10.0;
    A_OverRange := TRUE;
ELSE
    A_Engineering := INT_TO_REAL(A_Raw) * 10.0 / 4095.0;
END_IF;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_UnderRange THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

IF SubsystemBEnable AND CrossReady THEN
    B_ConfigError := B_LowThreshold >= B_HighThreshold;
    IF (NOT B_Enable) OR B_ConfigError THEN
        B_Heater := FALSE;
    ELSIF B_Temperature <= B_LowThreshold THEN
        B_Heater := TRUE;
    ELSIF B_Temperature >= B_HighThreshold THEN
        B_Heater := FALSE;
    END_IF;
ELSE
    B_Heater := FALSE;
    B_ConfigError := FALSE;
END_IF;

END_FUNCTION_BLOCK
