FUNCTION_BLOCK C05_B01_composite
VAR_INPUT
    A_Start : BOOL;
    A_Stop : BOOL;
    A_Permit : BOOL;
    A_Stage1Feedback : BOOL;
    B_Start : BOOL;
    B_Stop : BOOL;
    B_Overload : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Stage1 : BOOL;
    A_Stage2 : BOOL;
    A_Fault : BOOL;
    B_Main : BOOL;
    B_Star : BOOL;
    B_Delta : BOOL;
    B_Fault : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_FeedbackStable : TON;
    A_FeedbackTimeout : TON;
    B_StarTimer : TON;
    B_GapTimer : TON;
END_VAR

A_FeedbackStable(IN := A_Stage1Feedback AND A_Stage1, PT := T#300ms);
A_FeedbackTimeout(IN := A_Stage1 AND (NOT A_Stage1Feedback), PT := T#600ms);

IF A_FeedbackTimeout.Q THEN
    A_Fault := FALSE;
END_IF;
IF A_Stop AND (NOT A_Start) THEN
    A_Fault := FALSE;
END_IF;

IF A_Stop OR (NOT A_Permit) OR A_Fault THEN
    A_Stage1 := FALSE;
    A_Stage2 := FALSE;
ELSIF A_Start THEN
    A_Stage1 := TRUE;
    A_Stage2 := A_FeedbackStable.Q;
END_IF;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Stage1 THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

IF SubsystemBEnable AND CrossReady THEN
    B_StarTimer(IN := B_Main AND B_Star, PT := T#500ms);
    B_GapTimer(IN := B_Main AND (NOT B_Star) AND (NOT B_Delta), PT := T#200ms);

    IF B_Overload THEN
        B_Fault := TRUE;
    END_IF;
    IF B_Reset AND (NOT B_Start) AND (NOT B_Overload) THEN
        B_Fault := FALSE;
    END_IF;

    IF B_Stop OR B_Overload OR B_Fault THEN
        B_Main := FALSE;
        B_Star := FALSE;
        B_Delta := FALSE;
    ELSIF B_Start AND (NOT B_Main) THEN
        B_Main := TRUE;
        B_Star := TRUE;
        B_Delta := FALSE;
    ELSIF B_StarTimer.Q THEN
        B_Star := FALSE;
    ELSIF B_GapTimer.Q AND B_Main THEN
        B_Delta := TRUE;
    END_IF;
ELSE
    B_Main := FALSE;
    B_Star := FALSE;
    B_Delta := FALSE;
    B_Fault := FALSE;
END_IF;

END_FUNCTION_BLOCK
