FUNCTION_BLOCK C05_B07_composite
VAR_INPUT
    A_Start : BOOL;
    A_Stop : BOOL;
    A_Overload : BOOL;
    A_Reset : BOOL;
    B_MonitorEnable : BOOL;
    B_Heartbeat : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Main : BOOL;
    A_Star : BOOL;
    A_Delta : BOOL;
    A_Fault : BOOL;
    B_TimedOut : BOOL;
    B_Healthy : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_StarTimer : TON;
    A_GapTimer : TON;
    B_Watchdog : TON;
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
