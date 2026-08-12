FUNCTION_BLOCK C07_B19_composite
VAR_INPUT
    A_SensorA : REAL;
    A_SensorB : REAL;
    A_ValidA : BOOL;
    A_ValidB : BOOL;
    A_Enable : BOOL;
    A_MaxDifference : REAL;
    A_MaxRate : REAL;
    A_Reset : BOOL;
    B_Raw : INT;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_ProcessValue : REAL;
    A_ValidOutput : BOOL;
    A_Degraded : BOOL;
    A_Disagree : BOOL;
    A_RateTrip : BOOL;
    B_Engineering : REAL;
    B_UnderRange : BOOL;
    B_OverRange : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_Candidate : REAL;
    A_CandidateValid : BOOL;
    A_Ready : BOOL;
END_VAR

A_CandidateValid := FALSE;
A_Degraded := FALSE;
A_Disagree := FALSE;
IF A_Enable THEN
    IF A_ValidA AND A_ValidB THEN
        IF ABS(A_SensorA - A_SensorB) <= A_MaxDifference THEN
            A_Candidate := (A_SensorA + A_SensorB) / 2.0;
            A_CandidateValid := TRUE;
        ELSE
            A_Disagree := TRUE;
        END_IF;
    ELSIF A_ValidA THEN
        A_Candidate := A_SensorA; A_CandidateValid := TRUE; A_Degraded := TRUE;
    ELSIF A_ValidB THEN
        A_Candidate := A_SensorB; A_CandidateValid := TRUE; A_Degraded := TRUE;
    END_IF;
    IF A_CandidateValid AND (NOT A_RateTrip) THEN
        IF A_Ready AND (ABS(A_Candidate - A_ProcessValue) > A_MaxRate) THEN
            A_RateTrip := TRUE;
        ELSE
            A_ProcessValue := A_Candidate;
            A_Ready := TRUE;
        END_IF;
    END_IF;
ELSE
    A_Ready := FALSE;
    IF A_Reset THEN A_RateTrip := FALSE; END_IF;
END_IF;
A_ValidOutput := A_Enable AND A_CandidateValid AND (NOT A_RateTrip);
IF A_RateTrip THEN A_Degraded := FALSE; END_IF;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_ValidOutput THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := FALSE;

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
