FUNCTION_BLOCK C07_B14_composite
VAR_INPUT
    A_Temperature : REAL;
    A_LowThreshold : REAL;
    A_HighThreshold : REAL;
    A_Enable : BOOL;
    B_Value : REAL;
    B_Enable : BOOL;
    B_MaxRise : REAL;
    B_MaxFall : REAL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Heater : BOOL;
    A_ConfigError : BOOL;
    B_Delta : REAL;
    B_Trip : BOOL;
    B_Ready : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    B_Previous : REAL := 0.0;
END_VAR

A_ConfigError := A_LowThreshold >= A_HighThreshold;
IF (NOT A_Enable) OR A_ConfigError THEN
    A_Heater := FALSE;
ELSIF A_Temperature <= A_LowThreshold THEN
    A_Heater := TRUE;
ELSIF A_Temperature >= A_HighThreshold THEN
    A_Heater := FALSE;
END_IF;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Heater THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := FALSE;

IF SubsystemBEnable AND CrossReady THEN
    IF NOT B_Enable THEN
        B_Ready := FALSE;
        B_Delta := 0.0;
        IF B_Reset THEN
            B_Trip := FALSE;
        END_IF;
    ELSE
        IF NOT B_Ready THEN
            B_Previous := B_Value;
            B_Delta := 0.0;
            B_Ready := TRUE;
        ELSE
            B_Delta := B_Value - B_Previous;
            B_Previous := B_Value;
            IF (B_Delta > B_MaxRise) OR (B_Delta < (0.0 - B_MaxFall)) THEN
                B_Trip := TRUE;
            END_IF;
        END_IF;
    END_IF;
ELSE
    B_Delta := 0.0;
    B_Trip := FALSE;
    B_Ready := FALSE;
END_IF;

END_FUNCTION_BLOCK
