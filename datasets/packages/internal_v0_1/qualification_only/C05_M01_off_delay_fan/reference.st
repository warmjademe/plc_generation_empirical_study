FUNCTION_BLOCK C05_M01_off_delay_fan
VAR_INPUT
    Demand : BOOL;
    SafetyTrip : BOOL;
END_VAR
VAR_OUTPUT
    Fan : BOOL;
    RunOn : BOOL;
END_VAR
VAR
    OffTimer : TOF;
END_VAR

OffTimer(IN := Demand AND (NOT SafetyTrip), PT := T#300ms);
IF SafetyTrip THEN
    Fan := FALSE;
ELSE
    Fan := OffTimer.Q;
END_IF;
RunOn := (NOT Demand) AND Fan;

END_FUNCTION_BLOCK
