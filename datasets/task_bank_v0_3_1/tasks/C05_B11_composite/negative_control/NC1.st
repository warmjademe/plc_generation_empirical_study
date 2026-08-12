FUNCTION_BLOCK C05_B11_composite
VAR_INPUT
    A_Demand : BOOL;
    A_SafetyTrip : BOOL;
    B_MonitorEnable : BOOL;
    B_Heartbeat : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Fan : BOOL;
    A_RunOn : BOOL;
    B_TimedOut : BOOL;
    B_Healthy : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_OffTimer : TOF;
    B_Watchdog : TON;
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
