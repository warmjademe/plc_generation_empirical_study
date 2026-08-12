FUNCTION_BLOCK C07_B03_composite
VAR_INPUT
    A_SensorA : REAL;
    A_SensorB : REAL;
    A_ValidA : BOOL;
    A_ValidB : BOOL;
    A_MaxDifference : REAL;
    B_Temperature : REAL;
    B_LowThreshold : REAL;
    B_HighThreshold : REAL;
    B_Enable : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Selected : REAL;
    A_Degraded : BOOL;
    A_Disagree : BOOL;
    A_NoValidSensor : BOOL;
    B_Heater : BOOL;
    B_ConfigError : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR

A_Degraded := FALSE;
A_Disagree := FALSE;
A_NoValidSensor := FALSE;
IF A_ValidA AND A_ValidB THEN
    IF ABS(A_SensorA - A_SensorB) <= A_MaxDifference THEN
        A_Selected := (A_SensorA + A_SensorB) / 2.0;
    ELSE
        A_Disagree := FALSE;
    END_IF;
ELSIF A_ValidA THEN
    A_Selected := A_SensorA;
    A_Degraded := TRUE;
ELSIF A_ValidB THEN
    A_Selected := A_SensorB;
    A_Degraded := TRUE;
ELSE
    A_NoValidSensor := TRUE;
END_IF;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Degraded THEN
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
