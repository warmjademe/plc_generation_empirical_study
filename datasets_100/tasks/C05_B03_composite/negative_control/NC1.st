FUNCTION_BLOCK C05_B03_composite
VAR_INPUT
    A_Start : BOOL;
    A_Stop : BOOL;
    A_Permit : BOOL;
    A_Stage1Feedback : BOOL;
    B_MonitorEnable : BOOL;
    B_Heartbeat : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Stage1 : BOOL;
    A_Stage2 : BOOL;
    A_Fault : BOOL;
    B_TimedOut : BOOL;
    B_Healthy : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_FeedbackStable : TON;
    A_FeedbackTimeout : TON;
    B_Watchdog : TON;
END_VAR

A_FeedbackStable(IN := A_Stage1Feedback AND A_Stage1, PT := T#300ms);
A_FeedbackTimeout(IN := A_Stage1 AND (NOT A_Stage1Feedback), PT := T#600ms);

IF A_FeedbackTimeout.Q THEN
    A_Fault := TRUE;
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
CrossBlocked := FALSE;

IF SubsystemBEnable AND CrossReady THEN
    B_Watchdog(IN := B_MonitorEnable AND (NOT B_Heartbeat) AND (NOT B_TimedOut), PT := T#400ms);
    IF B_Watchdog.Q THEN
        B_TimedOut := TRUE;
    ELSIF B_Reset AND (NOT B_MonitorEnable) THEN
        B_TimedOut := FALSE;
    END_IF;
    B_Healthy := B_MonitorEnable AND (NOT B_TimedOut);
ELSE
    B_TimedOut := FALSE;
    B_Healthy := FALSE;
END_IF;

END_FUNCTION_BLOCK
