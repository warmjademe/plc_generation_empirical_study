FUNCTION_BLOCK C10_B15_composite
VAR_INPUT
    A_LowDemand : BOOL;
    A_HighDemand : BOOL;
    A_LeadIsPump1 : BOOL;
    A_Pump1Available : BOOL;
    A_Pump2Available : BOOL;
    B_Demand : BOOL;
    B_Pump1Available : BOOL;
    B_Pump2Available : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Pump1Run : BOOL;
    A_Pump2Run : BOOL;
    A_CapacityShortfall : BOOL;
    B_Pump1Run : BOOL;
    B_Pump2Run : BOOL;
    B_NextPump : INT;
    B_Unavailable : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    B_PrevDemand : BOOL;
END_VAR

A_Pump1Run := FALSE;
A_Pump2Run := FALSE;
IF A_HighDemand THEN
    A_Pump1Run := A_Pump1Available;
    A_Pump2Run := A_Pump2Available;
ELSIF A_LowDemand THEN
    IF A_LeadIsPump1 THEN
        IF A_Pump1Available THEN A_Pump1Run := FALSE;
        ELSIF A_Pump2Available THEN A_Pump2Run := TRUE;
        END_IF;
    ELSE
        IF A_Pump2Available THEN A_Pump2Run := TRUE;
        ELSIF A_Pump1Available THEN A_Pump1Run := TRUE;
        END_IF;
    END_IF;
END_IF;
A_CapacityShortfall := (A_HighDemand AND ((NOT A_Pump1Available) OR (NOT A_Pump2Available))) OR
    (A_LowDemand AND (NOT A_HighDemand) AND (NOT A_Pump1Available) AND (NOT A_Pump2Available));

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Pump1Run THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

IF SubsystemBEnable AND CrossReady THEN
    IF (B_NextPump <> 1) AND (B_NextPump <> 2) THEN
        B_NextPump := 1;
    END_IF;
    IF B_Reset AND (NOT B_Demand) THEN
        B_NextPump := 1;
    END_IF;
    IF NOT B_Demand THEN
        B_Pump1Run := FALSE;
        B_Pump2Run := FALSE;
    ELSIF NOT B_PrevDemand THEN
        IF (B_NextPump = 1) AND B_Pump1Available THEN
            B_Pump1Run := TRUE;
            B_Pump2Run := FALSE;
            B_NextPump := 2;
        ELSIF B_Pump2Available THEN
            B_Pump1Run := FALSE;
            B_Pump2Run := TRUE;
            B_NextPump := 1;
        ELSIF B_Pump1Available THEN
            B_Pump1Run := TRUE;
            B_Pump2Run := FALSE;
            B_NextPump := 2;
        ELSE
            B_Pump1Run := FALSE;
            B_Pump2Run := FALSE;
        END_IF;
    END_IF;
    B_Unavailable := B_Demand AND (NOT B_Pump1Available) AND (NOT B_Pump2Available);
    B_PrevDemand := B_Demand;
ELSE
    B_Pump1Run := FALSE;
    B_Pump2Run := FALSE;
    B_NextPump := 0;
    B_Unavailable := FALSE;
END_IF;

END_FUNCTION_BLOCK
