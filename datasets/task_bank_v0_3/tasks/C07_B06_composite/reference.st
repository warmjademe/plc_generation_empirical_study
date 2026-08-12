FUNCTION_BLOCK C07_B06_composite
VAR_INPUT
    A_Value : REAL;
    A_Enable : BOOL;
    A_MaxRise : REAL;
    A_MaxFall : REAL;
    A_Reset : BOOL;
    B_Raw : INT;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Delta : REAL;
    A_Trip : BOOL;
    A_Ready : BOOL;
    B_Engineering : REAL;
    B_UnderRange : BOOL;
    B_OverRange : BOOL;
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
