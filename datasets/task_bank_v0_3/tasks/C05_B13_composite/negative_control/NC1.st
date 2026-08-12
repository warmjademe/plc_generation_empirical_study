FUNCTION_BLOCK C05_B13_composite
VAR_INPUT
    A_MonitorEnable : BOOL;
    A_Heartbeat : BOOL;
    A_Reset : BOOL;
    B_Start : BOOL;
    B_Stop : BOOL;
    B_Permit : BOOL;
    B_Stage1Feedback : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_TimedOut : BOOL;
    A_Healthy : BOOL;
    B_Stage1 : BOOL;
    B_Stage2 : BOOL;
    B_Fault : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_Watchdog : TON;
    B_FeedbackStable : TON;
    B_FeedbackTimeout : TON;
END_VAR

A_Watchdog(IN := A_MonitorEnable AND (NOT A_Heartbeat) AND (NOT A_TimedOut), PT := T#400ms);
IF A_Watchdog.Q THEN
    A_TimedOut := FALSE;
ELSIF A_Reset AND (NOT A_MonitorEnable) THEN
    A_TimedOut := FALSE;
END_IF;
A_Healthy := A_MonitorEnable AND (NOT A_TimedOut);

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_TimedOut THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

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
