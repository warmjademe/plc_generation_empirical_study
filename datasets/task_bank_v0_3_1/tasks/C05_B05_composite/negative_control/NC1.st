FUNCTION_BLOCK C05_B05_composite
VAR_INPUT
    A_Start : BOOL;
    A_Stop : BOOL;
    A_Overload : BOOL;
    A_Reset : BOOL;
    B_Start : BOOL;
    B_Stop : BOOL;
    B_Permit : BOOL;
    B_Stage1Feedback : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Main : BOOL;
    A_Star : BOOL;
    A_Delta : BOOL;
    A_Fault : BOOL;
    B_Stage1 : BOOL;
    B_Stage2 : BOOL;
    B_Fault : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_StarTimer : TON;
    A_GapTimer : TON;
    B_FeedbackStable : TON;
    B_FeedbackTimeout : TON;
END_VAR

A_StarTimer(IN := A_Main AND A_Star, PT := T#500ms);
A_GapTimer(IN := A_Main AND (NOT A_Star) AND (NOT A_Delta), PT := T#200ms);

IF A_Overload THEN
    A_Fault := TRUE;
END_IF;
IF A_Reset AND (NOT A_Start) AND (NOT A_Overload) THEN
    A_Fault := FALSE;
END_IF;

IF A_Stop OR A_Overload OR A_Fault THEN
    A_Main := FALSE;
    A_Star := FALSE;
    A_Delta := FALSE;
ELSIF A_Start AND (NOT A_Main) THEN
    A_Main := TRUE;
    A_Star := TRUE;
    A_Delta := FALSE;
ELSIF A_StarTimer.Q THEN
    A_Star := FALSE;
ELSIF A_GapTimer.Q AND A_Main THEN
    A_Delta := TRUE;
END_IF;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Main THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := FALSE;

IF SubsystemBEnable AND CrossReady THEN
    B_FeedbackStable(IN := B_Stage1Feedback AND B_Stage1, PT := T#300ms);
    B_FeedbackTimeout(IN := B_Stage1 AND (NOT B_Stage1Feedback), PT := T#600ms);

    IF B_FeedbackTimeout.Q THEN
        B_Fault := TRUE;
    END_IF;
    IF B_Stop AND (NOT B_Start) THEN
        B_Fault := FALSE;
    END_IF;

    IF B_Stop OR (NOT B_Permit) OR B_Fault THEN
        B_Stage1 := FALSE;
        B_Stage2 := FALSE;
    ELSIF B_Start THEN
        B_Stage1 := TRUE;
        B_Stage2 := B_FeedbackStable.Q;
    END_IF;
ELSE
    B_Stage1 := FALSE;
    B_Stage2 := FALSE;
    B_Fault := FALSE;
END_IF;

END_FUNCTION_BLOCK
