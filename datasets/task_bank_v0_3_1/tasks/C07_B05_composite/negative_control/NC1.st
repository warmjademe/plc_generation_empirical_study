FUNCTION_BLOCK C07_B05_composite
VAR_INPUT
    A_Value : REAL;
    A_Enable : BOOL;
    A_MaxRise : REAL;
    A_MaxFall : REAL;
    A_Reset : BOOL;
    B_SensorA : REAL;
    B_SensorB : REAL;
    B_ValidA : BOOL;
    B_ValidB : BOOL;
    B_MaxDifference : REAL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Delta : REAL;
    A_Trip : BOOL;
    A_Ready : BOOL;
    B_Selected : REAL;
    B_Degraded : BOOL;
    B_Disagree : BOOL;
    B_NoValidSensor : BOOL;
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
        A_Ready := TRUE;
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
CrossBlocked := FALSE;

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
