FUNCTION_BLOCK C10_B11_composite
VAR_INPUT
    A_Demand : BOOL;
    A_Pump1Available : BOOL;
    A_Pump2Available : BOOL;
    A_Reset : BOOL;
    B_LowDemand : BOOL;
    B_HighDemand : BOOL;
    B_LeadIsPump1 : BOOL;
    B_Pump1Available : BOOL;
    B_Pump2Available : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Pump1Run : BOOL;
    A_Pump2Run : BOOL;
    A_NextPump : INT;
    A_Unavailable : BOOL;
    B_Pump1Run : BOOL;
    B_Pump2Run : BOOL;
    B_CapacityShortfall : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PrevDemand : BOOL;
END_VAR

IF (A_NextPump <> 1) AND (A_NextPump <> 2) THEN
    A_NextPump := 1;
END_IF;
IF A_Reset AND (NOT A_Demand) THEN
    A_NextPump := 1;
END_IF;
IF NOT A_Demand THEN
    A_Pump1Run := FALSE;
    A_Pump2Run := FALSE;
ELSIF NOT A_PrevDemand THEN
    IF (A_NextPump = 1) AND A_Pump1Available THEN
        A_Pump1Run := TRUE;
        A_Pump2Run := FALSE;
        A_NextPump := 2;
    ELSIF A_Pump2Available THEN
        A_Pump1Run := FALSE;
        A_Pump2Run := TRUE;
        A_NextPump := 1;
    ELSIF A_Pump1Available THEN
        A_Pump1Run := TRUE;
        A_Pump2Run := FALSE;
        A_NextPump := 2;
    ELSE
        A_Pump1Run := FALSE;
        A_Pump2Run := FALSE;
    END_IF;
END_IF;
A_Unavailable := A_Demand AND (NOT A_Pump1Available) AND (NOT A_Pump2Available);
A_PrevDemand := A_Demand;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Pump1Run THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := FALSE;

IF SubsystemBEnable AND CrossReady THEN
    B_Pump1Run := FALSE;
    B_Pump2Run := FALSE;
    IF B_HighDemand THEN
        B_Pump1Run := B_Pump1Available;
        B_Pump2Run := B_Pump2Available;
    ELSIF B_LowDemand THEN
        IF B_LeadIsPump1 THEN
            IF B_Pump1Available THEN B_Pump1Run := TRUE;
            ELSIF B_Pump2Available THEN B_Pump2Run := TRUE;
            END_IF;
        ELSE
            IF B_Pump2Available THEN B_Pump2Run := TRUE;
            ELSIF B_Pump1Available THEN B_Pump1Run := TRUE;
            END_IF;
        END_IF;
    END_IF;
    B_CapacityShortfall := (B_HighDemand AND ((NOT B_Pump1Available) OR (NOT B_Pump2Available))) OR
        (B_LowDemand AND (NOT B_HighDemand) AND (NOT B_Pump1Available) AND (NOT B_Pump2Available));
ELSE
    B_Pump1Run := FALSE;
    B_Pump2Run := FALSE;
    B_CapacityShortfall := FALSE;
END_IF;

END_FUNCTION_BLOCK
