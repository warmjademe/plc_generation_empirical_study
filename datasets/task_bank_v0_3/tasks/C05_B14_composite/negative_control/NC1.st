FUNCTION_BLOCK C05_B14_composite
VAR_INPUT
    A_MonitorEnable : BOOL;
    A_Heartbeat : BOOL;
    A_Reset : BOOL;
    B_Start : BOOL;
    B_Stop : BOOL;
    B_Overload : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_TimedOut : BOOL;
    A_Healthy : BOOL;
    B_Main : BOOL;
    B_Star : BOOL;
    B_Delta : BOOL;
    B_Fault : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_Watchdog : TON;
    B_StarTimer : TON;
    B_GapTimer : TON;
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
