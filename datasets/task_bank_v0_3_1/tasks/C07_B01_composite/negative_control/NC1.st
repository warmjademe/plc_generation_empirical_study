FUNCTION_BLOCK C07_B01_composite
VAR_INPUT
    A_SensorA : REAL;
    A_SensorB : REAL;
    A_ValidA : BOOL;
    A_ValidB : BOOL;
    A_MaxDifference : REAL;
    B_Value : REAL;
    B_Enable : BOOL;
    B_MaxRise : REAL;
    B_MaxFall : REAL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Selected : REAL;
    A_Degraded : BOOL;
    A_Disagree : BOOL;
    A_NoValidSensor : BOOL;
    B_Delta : REAL;
    B_Trip : BOOL;
    B_Ready : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    B_Previous : REAL := 0.0;
END_VAR

A_Degraded := FALSE;
A_Disagree := FALSE;
A_NoValidSensor := FALSE;
IF A_ValidA AND A_ValidB THEN
    IF ABS(A_SensorA - A_SensorB) <= A_MaxDifference THEN
        A_Selected := (A_SensorA + A_SensorB) / 2.0;
    ELSE
        A_Disagree := TRUE;
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
