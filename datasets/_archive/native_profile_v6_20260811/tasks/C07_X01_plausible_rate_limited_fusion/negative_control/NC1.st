FUNCTION_BLOCK C07_X01_plausible_rate_limited_fusion
VAR_INPUT
    SensorA : REAL;
    SensorB : REAL;
    ValidA : BOOL;
    ValidB : BOOL;
    Enable : BOOL;
    MaxDifference : REAL;
    MaxRate : REAL;
    Reset : BOOL;
END_VAR
VAR_OUTPUT
    ProcessValue : REAL;
    ValidOutput : BOOL;
    Degraded : BOOL;
    Disagree : BOOL;
    RateTrip : BOOL;
END_VAR
VAR
    Candidate : REAL;
    CandidateValid : BOOL;
    Ready : BOOL;
END_VAR

CandidateValid := FALSE;
Degraded := FALSE;
Disagree := FALSE;
IF Enable THEN
    IF ValidA AND ValidB THEN
        IF ABS(SensorA - SensorB) <= MaxDifference THEN
            Candidate := (SensorA + SensorB) / 2.0;
            CandidateValid := FALSE;
        ELSE
            Disagree := TRUE;
        END_IF;
    ELSIF ValidA THEN
        Candidate := SensorA; CandidateValid := TRUE; Degraded := TRUE;
    ELSIF ValidB THEN
        Candidate := SensorB; CandidateValid := TRUE; Degraded := TRUE;
    END_IF;
    IF CandidateValid AND (NOT RateTrip) THEN
        IF Ready AND (ABS(Candidate - ProcessValue) > MaxRate) THEN
            RateTrip := TRUE;
        ELSE
            ProcessValue := Candidate;
            Ready := TRUE;
        END_IF;
    END_IF;
ELSE
    Ready := FALSE;
    IF Reset THEN RateTrip := FALSE; END_IF;
END_IF;
ValidOutput := Enable AND CandidateValid AND (NOT RateTrip);
IF RateTrip THEN Degraded := FALSE; END_IF;

END_FUNCTION_BLOCK
