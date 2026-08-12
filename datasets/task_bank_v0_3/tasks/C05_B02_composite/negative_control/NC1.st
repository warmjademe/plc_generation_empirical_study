FUNCTION_BLOCK C05_B02_composite
VAR_INPUT
    A_Start : BOOL;
    A_Stop : BOOL;
    A_Permit : BOOL;
    A_Stage1Feedback : BOOL;
    B_Demand : BOOL;
    B_SafetyTrip : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Stage1 : BOOL;
    A_Stage2 : BOOL;
    A_Fault : BOOL;
    B_Fan : BOOL;
    B_RunOn : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_FeedbackStable : TON;
    A_FeedbackTimeout : TON;
    B_OffTimer : TOF;
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
    B_OffTimer(IN := B_Demand AND (NOT B_SafetyTrip), PT := T#300ms);
    IF B_SafetyTrip THEN
        B_Fan := FALSE;
    ELSE
        B_Fan := B_OffTimer.Q;
    END_IF;
    B_RunOn := (NOT B_Demand) AND B_Fan;
ELSE
    B_Fan := FALSE;
    B_RunOn := FALSE;
END_IF;

END_FUNCTION_BLOCK
