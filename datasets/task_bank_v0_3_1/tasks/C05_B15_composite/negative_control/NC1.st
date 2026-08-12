FUNCTION_BLOCK C05_B15_composite
VAR_INPUT
    A_MonitorEnable : BOOL;
    A_Heartbeat : BOOL;
    A_Reset : BOOL;
    B_Demand : BOOL;
    B_SafetyTrip : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_TimedOut : BOOL;
    A_Healthy : BOOL;
    B_Fan : BOOL;
    B_RunOn : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_Watchdog : TON;
    B_OffTimer : TOF;
END_VAR

A_Watchdog(IN := A_MonitorEnable AND (NOT A_Heartbeat) AND (NOT A_TimedOut), PT := T#400ms);
IF A_Watchdog.Q THEN
    A_TimedOut := TRUE;
ELSIF A_Reset AND (NOT A_MonitorEnable) THEN
    A_TimedOut := FALSE;
END_IF;
A_Healthy := A_MonitorEnable AND (NOT A_TimedOut);

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_TimedOut THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := FALSE;

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
