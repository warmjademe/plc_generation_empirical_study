FUNCTION_BLOCK C07_B15_composite
VAR_INPUT
    A_Temperature : REAL;
    A_LowThreshold : REAL;
    A_HighThreshold : REAL;
    A_Enable : BOOL;
    B_Raw : INT;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Heater : BOOL;
    A_ConfigError : BOOL;
    B_Engineering : REAL;
    B_UnderRange : BOOL;
    B_OverRange : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR

A_ConfigError := A_LowThreshold >= A_HighThreshold;
IF (NOT A_Enable) OR A_ConfigError THEN
    A_Heater := FALSE;
ELSIF A_Temperature <= A_LowThreshold THEN
    A_Heater := FALSE;
ELSIF A_Temperature >= A_HighThreshold THEN
    A_Heater := FALSE;
END_IF;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Heater THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

IF SubsystemBEnable AND CrossReady THEN
    B_UnderRange := FALSE;
    B_OverRange := FALSE;
    IF B_Raw < 0 THEN
        B_Engineering := 0.0;
        B_UnderRange := TRUE;
    ELSIF B_Raw > 4095 THEN
        B_Engineering := 10.0;
        B_OverRange := TRUE;
    ELSE
        B_Engineering := INT_TO_REAL(B_Raw) * 10.0 / 4095.0;
    END_IF;
ELSE
    B_Engineering := 0.0;
    B_UnderRange := FALSE;
    B_OverRange := FALSE;
END_IF;

END_FUNCTION_BLOCK
