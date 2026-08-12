FUNCTION_BLOCK C07_B16_composite
VAR_INPUT
    A_Temperature : REAL;
    A_LowThreshold : REAL;
    A_HighThreshold : REAL;
    A_Enable : BOOL;
    B_SensorA : REAL;
    B_SensorB : REAL;
    B_ValidA : BOOL;
    B_ValidB : BOOL;
    B_Enable : BOOL;
    B_MaxDifference : REAL;
    B_MaxRate : REAL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Heater : BOOL;
    A_ConfigError : BOOL;
    B_ProcessValue : REAL;
    B_ValidOutput : BOOL;
    B_Degraded : BOOL;
    B_Disagree : BOOL;
    B_RateTrip : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    B_Candidate : REAL;
    B_CandidateValid : BOOL;
    B_Ready : BOOL;
END_VAR

A_ConfigError := A_LowThreshold >= A_HighThreshold;
IF (NOT A_Enable) OR A_ConfigError THEN
    A_Heater := FALSE;
ELSIF A_Temperature <= A_LowThreshold THEN
    A_Heater := FALSE;
ELSIF A_Temperature >= A_HighThreshold THEN
    A_Heater := FALSE;
END_IF;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Heater THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

IF SubsystemBEnable AND CrossReady THEN
    B_CandidateValid := FALSE;
    B_Degraded := FALSE;
    B_Disagree := FALSE;
    IF B_Enable THEN
        IF B_ValidA AND B_ValidB THEN
            IF ABS(B_SensorA - B_SensorB) <= B_MaxDifference THEN
                B_Candidate := (B_SensorA + B_SensorB) / 2.0;
                B_CandidateValid := TRUE;
            ELSE
                B_Disagree := TRUE;
            END_IF;
        ELSIF B_ValidA THEN
            B_Candidate := B_SensorA; B_CandidateValid := TRUE; B_Degraded := TRUE;
        ELSIF B_ValidB THEN
            B_Candidate := B_SensorB; B_CandidateValid := TRUE; B_Degraded := TRUE;
        END_IF;
        IF B_CandidateValid AND (NOT B_RateTrip) THEN
            IF B_Ready AND (ABS(B_Candidate - B_ProcessValue) > B_MaxRate) THEN
                B_RateTrip := TRUE;
            ELSE
                B_ProcessValue := B_Candidate;
                B_Ready := TRUE;
            END_IF;
        END_IF;
    ELSE
        B_Ready := FALSE;
        IF B_Reset THEN B_RateTrip := FALSE; END_IF;
    END_IF;
    B_ValidOutput := B_Enable AND B_CandidateValid AND (NOT B_RateTrip);
    IF B_RateTrip THEN B_Degraded := FALSE; END_IF;
ELSE
    B_ProcessValue := 0.0;
    B_ValidOutput := FALSE;
    B_Degraded := FALSE;
    B_Disagree := FALSE;
    B_RateTrip := FALSE;
END_IF;

END_FUNCTION_BLOCK
