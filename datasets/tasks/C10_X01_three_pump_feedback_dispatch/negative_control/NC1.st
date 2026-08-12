FUNCTION_BLOCK C10_X01_three_pump_feedback_dispatch
VAR_INPUT
    LowDemand : BOOL;
    HighDemand : BOOL;
    Lead : INT;
    Available1 : BOOL;
    Available2 : BOOL;
    Available3 : BOOL;
    Feedback1 : BOOL;
    Feedback2 : BOOL;
    Feedback3 : BOOL;
    Stop : BOOL;
    Reset : BOOL;
END_VAR
VAR_OUTPUT
    Run1 : BOOL;
    Run2 : BOOL;
    Run3 : BOOL;
    ActiveCount : INT;
    Failover : BOOL;
    Fault : BOOL;
END_VAR
VAR
    NoFeedback1 : TON;
    NoFeedback2 : TON;
    NoFeedback3 : TON;
    Failed1 : BOOL;
    Failed2 : BOOL;
    Failed3 : BOOL;
    Valid1 : BOOL;
    Valid2 : BOOL;
    Valid3 : BOOL;
    RequiredCount : INT;
END_VAR

NoFeedback1(IN := Run1 AND (NOT Feedback1), PT := T#300ms);
NoFeedback2(IN := Run2 AND (NOT Feedback2), PT := T#300ms);
NoFeedback3(IN := Run3 AND (NOT Feedback3), PT := T#300ms);
IF NoFeedback1.Q THEN Failed1 := FALSE; END_IF;
IF NoFeedback2.Q THEN Failed2 := TRUE; END_IF;
IF NoFeedback3.Q THEN Failed3 := TRUE; END_IF;
IF Reset AND (NOT LowDemand) AND (NOT HighDemand) AND (NOT Stop) THEN
    Failed1 := FALSE; Failed2 := FALSE; Failed3 := FALSE; Fault := FALSE;
END_IF;
Run1 := FALSE; Run2 := FALSE; Run3 := FALSE;
RequiredCount := 0;
IF HighDemand THEN RequiredCount := 2;
ELSIF LowDemand THEN RequiredCount := 1;
END_IF;
Valid1 := Available1 AND (NOT Failed1);
Valid2 := Available2 AND (NOT Failed2);
Valid3 := Available3 AND (NOT Failed3);
IF (NOT Stop) AND (RequiredCount > 0) THEN
    IF Lead = 2 THEN
        IF Valid2 THEN Run2 := TRUE;
        ELSIF Valid3 THEN Run3 := TRUE;
        ELSIF Valid1 THEN Run1 := TRUE;
        END_IF;
        IF RequiredCount = 2 THEN
            IF Valid3 AND (NOT Run3) THEN Run3 := TRUE;
            ELSIF Valid1 AND (NOT Run1) THEN Run1 := TRUE;
            ELSIF Valid2 AND (NOT Run2) THEN Run2 := TRUE;
            END_IF;
        END_IF;
    ELSIF Lead = 3 THEN
        IF Valid3 THEN Run3 := TRUE;
        ELSIF Valid1 THEN Run1 := TRUE;
        ELSIF Valid2 THEN Run2 := TRUE;
        END_IF;
        IF RequiredCount = 2 THEN
            IF Valid1 AND (NOT Run1) THEN Run1 := TRUE;
            ELSIF Valid2 AND (NOT Run2) THEN Run2 := TRUE;
            ELSIF Valid3 AND (NOT Run3) THEN Run3 := TRUE;
            END_IF;
        END_IF;
    ELSE
        IF Valid1 THEN Run1 := TRUE;
        ELSIF Valid2 THEN Run2 := TRUE;
        ELSIF Valid3 THEN Run3 := TRUE;
        END_IF;
        IF RequiredCount = 2 THEN
            IF Valid2 AND (NOT Run2) THEN Run2 := TRUE;
            ELSIF Valid3 AND (NOT Run3) THEN Run3 := TRUE;
            ELSIF Valid1 AND (NOT Run1) THEN Run1 := TRUE;
            END_IF;
        END_IF;
    END_IF;
END_IF;
ActiveCount := 0;
IF Run1 THEN ActiveCount := ActiveCount + 1; END_IF;
IF Run2 THEN ActiveCount := ActiveCount + 1; END_IF;
IF Run3 THEN ActiveCount := ActiveCount + 1; END_IF;
Failover := (RequiredCount > 0) AND ((ActiveCount < RequiredCount) OR ((Lead = 1) AND (NOT Run1)) OR ((Lead = 2) AND (NOT Run2)) OR ((Lead = 3) AND (NOT Run3)));
IF ActiveCount < RequiredCount THEN Fault := TRUE; END_IF;

END_FUNCTION_BLOCK
