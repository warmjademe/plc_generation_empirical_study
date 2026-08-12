FUNCTION_BLOCK C07_B10_composite
VAR_INPUT
    A_Raw : INT;
    B_Value : REAL;
    B_Enable : BOOL;
    B_MaxRise : REAL;
    B_MaxFall : REAL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Engineering : REAL;
    A_UnderRange : BOOL;
    A_OverRange : BOOL;
    B_Delta : REAL;
    B_Trip : BOOL;
    B_Ready : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    B_Previous : REAL := 0.0;
END_VAR

A_UnderRange := FALSE;
A_OverRange := FALSE;
IF A_Raw < 0 THEN
    A_Engineering := 0.0;
    A_UnderRange := TRUE;
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
