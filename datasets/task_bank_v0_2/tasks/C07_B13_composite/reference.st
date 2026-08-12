FUNCTION_BLOCK C07_B13_composite
VAR_INPUT
    A_Temperature : REAL;
    A_LowThreshold : REAL;
    A_HighThreshold : REAL;
    A_Enable : BOOL;
    B_SensorA : REAL;
    B_SensorB : REAL;
    B_ValidA : BOOL;
    B_ValidB : BOOL;
    B_MaxDifference : REAL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Heater : BOOL;
    A_ConfigError : BOOL;
    B_Selected : REAL;
    B_Degraded : BOOL;
    B_Disagree : BOOL;
    B_NoValidSensor : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
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
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

IF SubsystemBEnable AND CrossReady THEN
    B_Degraded := FALSE;
    B_Disagree := FALSE;
    B_NoValidSensor := FALSE;
    IF B_ValidA AND B_ValidB THEN
        IF ABS(B_SensorA - B_SensorB) <= B_MaxDifference THEN
            B_Selected := (B_SensorA + B_SensorB) / 2.0;
        ELSE
            B_Disagree := TRUE;
        END_IF;
    ELSIF B_ValidA THEN
        B_Selected := B_SensorA;
        B_Degraded := TRUE;
    ELSIF B_ValidB THEN
        B_Selected := B_SensorB;
        B_Degraded := TRUE;
    ELSE
        B_NoValidSensor := TRUE;
    END_IF;
ELSE
    B_Selected := 0.0;
    B_Degraded := FALSE;
    B_Disagree := FALSE;
    B_NoValidSensor := FALSE;
END_IF;

END_FUNCTION_BLOCK
