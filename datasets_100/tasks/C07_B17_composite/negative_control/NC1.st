FUNCTION_BLOCK C07_B17_composite
VAR_INPUT
    A_SensorA : REAL;
    A_SensorB : REAL;
    A_ValidA : BOOL;
    A_ValidB : BOOL;
    A_Enable : BOOL;
    A_MaxDifference : REAL;
    A_MaxRate : REAL;
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
    A_ProcessValue : REAL;
    A_ValidOutput : BOOL;
    A_Degraded : BOOL;
    A_Disagree : BOOL;
    A_RateTrip : BOOL;
    B_Selected : REAL;
    B_Degraded : BOOL;
    B_Disagree : BOOL;
    B_NoValidSensor : BOOL;
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
