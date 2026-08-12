FUNCTION_BLOCK C05_B06_composite
VAR_INPUT
    A_Start : BOOL;
    A_Stop : BOOL;
    A_Overload : BOOL;
    A_Reset : BOOL;
    B_Demand : BOOL;
    B_SafetyTrip : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Main : BOOL;
    A_Star : BOOL;
    A_Delta : BOOL;
    A_Fault : BOOL;
    B_Fan : BOOL;
    B_RunOn : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_StarTimer : TON;
    A_GapTimer : TON;
    B_OffTimer : TOF;
END_VAR

A_StarTimer(IN := A_Main AND A_Star, PT := T#500ms);
A_GapTimer(IN := A_Main AND (NOT A_Star) AND (NOT A_Delta), PT := T#200ms);

IF A_Overload THEN
    A_Fault := FALSE;
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
