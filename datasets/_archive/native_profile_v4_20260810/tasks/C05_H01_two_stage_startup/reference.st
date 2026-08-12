FUNCTION_BLOCK C05_H01_two_stage_startup
VAR_INPUT
    Start : BOOL;
    Stop : BOOL;
    Permit : BOOL;
    Stage1Feedback : BOOL;
END_VAR
VAR_OUTPUT
    Stage1 : BOOL;
    Stage2 : BOOL;
    Fault : BOOL;
END_VAR
VAR
    FeedbackStable : TON;
    FeedbackTimeout : TON;
END_VAR

FeedbackStable(IN := Stage1Feedback AND Stage1, PT := T#300ms);
FeedbackTimeout(IN := Stage1 AND (NOT Stage1Feedback), PT := T#600ms);

IF FeedbackTimeout.Q THEN
    Fault := TRUE;
END_IF;
IF Stop AND (NOT Start) THEN
    Fault := FALSE;
END_IF;

IF Stop OR (NOT Permit) OR Fault THEN
    Stage1 := FALSE;
    Stage2 := FALSE;
ELSIF Start THEN
    Stage1 := TRUE;
    Stage2 := FeedbackStable.Q;
END_IF;

END_FUNCTION_BLOCK
