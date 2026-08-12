FUNCTION_BLOCK C05_B09_composite
VAR_INPUT
    A_Demand : BOOL;
    A_SafetyTrip : BOOL;
    B_Start : BOOL;
    B_Stop : BOOL;
    B_Permit : BOOL;
    B_Stage1Feedback : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Fan : BOOL;
    A_RunOn : BOOL;
    B_Stage1 : BOOL;
    B_Stage2 : BOOL;
    B_Fault : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_OffTimer : TOF;
    B_FeedbackStable : TON;
    B_FeedbackTimeout : TON;
END_VAR

A_OffTimer(IN := A_Demand AND (NOT A_SafetyTrip), PT := T#300ms);
IF A_SafetyTrip THEN
    A_Fan := FALSE;
ELSE
    A_Fan := A_OffTimer.Q;
END_IF;
A_RunOn := (NOT A_Demand) AND A_Fan;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Fan THEN
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
