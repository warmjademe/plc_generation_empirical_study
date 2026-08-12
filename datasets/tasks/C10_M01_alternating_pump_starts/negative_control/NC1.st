FUNCTION_BLOCK C10_M01_alternating_pump_starts
VAR_INPUT
    Demand : BOOL;
    Pump1Available : BOOL;
    Pump2Available : BOOL;
    Reset : BOOL;
END_VAR
VAR_OUTPUT
    Pump1Run : BOOL;
    Pump2Run : BOOL;
    NextPump : INT;
    Unavailable : BOOL;
END_VAR
VAR
    PrevDemand : BOOL;
END_VAR

IF (NextPump <> 1) AND (NextPump <> 2) THEN
    NextPump := 1;
END_IF;
IF Reset AND (NOT Demand) THEN
    NextPump := 1;
END_IF;
IF NOT Demand THEN
    Pump1Run := FALSE;
    Pump2Run := FALSE;
ELSIF NOT PrevDemand THEN
    IF (NextPump = 1) AND Pump1Available THEN
        Pump1Run := FALSE;
        Pump2Run := FALSE;
        NextPump := 2;
    ELSIF Pump2Available THEN
        Pump1Run := FALSE;
        Pump2Run := TRUE;
        NextPump := 1;
    ELSIF Pump1Available THEN
        Pump1Run := TRUE;
        Pump2Run := FALSE;
        NextPump := 2;
    ELSE
        Pump1Run := FALSE;
        Pump2Run := FALSE;
    END_IF;
END_IF;
Unavailable := Demand AND (NOT Pump1Available) AND (NOT Pump2Available);
PrevDemand := Demand;

END_FUNCTION_BLOCK
