FUNCTION_BLOCK C07_B07_composite
VAR_INPUT
    A_Value : REAL;
    A_Enable : BOOL;
    A_MaxRise : REAL;
    A_MaxFall : REAL;
    A_Reset : BOOL;
    B_Temperature : REAL;
    B_LowThreshold : REAL;
    B_HighThreshold : REAL;
    B_Enable : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Delta : REAL;
    A_Trip : BOOL;
    A_Ready : BOOL;
    B_Heater : BOOL;
    B_ConfigError : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_Previous : REAL := 0.0;
END_VAR

IF NOT A_Enable THEN
    A_Ready := FALSE;
    A_Delta := 0.0;
    IF A_Reset THEN
        A_Trip := FALSE;
    END_IF;
ELSE
    IF NOT A_Ready THEN
        A_Previous := A_Value;
        A_Delta := 0.0;
        A_Ready := FALSE;
    ELSE
        A_Delta := A_Value - A_Previous;
        A_Previous := A_Value;
        IF (A_Delta > A_MaxRise) OR (A_Delta < (0.0 - A_MaxFall)) THEN
            A_Trip := TRUE;
        END_IF;
    END_IF;
END_IF;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Trip THEN
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
