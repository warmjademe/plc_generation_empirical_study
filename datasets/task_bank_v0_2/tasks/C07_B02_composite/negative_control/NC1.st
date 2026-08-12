FUNCTION_BLOCK C07_B02_composite
VAR_INPUT
    A_SensorA : REAL;
    A_SensorB : REAL;
    A_ValidA : BOOL;
    A_ValidB : BOOL;
    A_MaxDifference : REAL;
    B_Raw : INT;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Selected : REAL;
    A_Degraded : BOOL;
    A_Disagree : BOOL;
    A_NoValidSensor : BOOL;
    B_Engineering : REAL;
    B_UnderRange : BOOL;
    B_OverRange : BOOL;
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
