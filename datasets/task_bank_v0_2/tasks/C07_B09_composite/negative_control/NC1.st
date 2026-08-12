FUNCTION_BLOCK C07_B09_composite
VAR_INPUT
    A_Raw : INT;
    B_SensorA : REAL;
    B_SensorB : REAL;
    B_ValidA : BOOL;
    B_ValidB : BOOL;
    B_MaxDifference : REAL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Engineering : REAL;
    A_UnderRange : BOOL;
    A_OverRange : BOOL;
    B_Selected : REAL;
    B_Degraded : BOOL;
    B_Disagree : BOOL;
    B_NoValidSensor : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR

A_UnderRange := FALSE;
A_OverRange := FALSE;
IF A_Raw < 0 THEN
    A_Engineering := 0.0;
    A_UnderRange := FALSE;
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
