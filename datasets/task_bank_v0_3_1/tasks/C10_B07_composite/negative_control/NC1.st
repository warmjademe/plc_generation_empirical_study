FUNCTION_BLOCK C10_B07_composite
VAR_INPUT
    A_RequestA : BOOL;
    A_RequestB : BOOL;
    A_Done : BOOL;
    A_Emergency : BOOL;
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
    A_GrantA : BOOL;
    A_GrantB : BOOL;
    A_Busy : BOOL;
    A_Turn : INT;
    A_LockedOut : BOOL;
    B_Pump1Run : BOOL;
    B_Pump2Run : BOOL;
    B_CapacityShortfall : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR

IF (A_Turn <> 1) AND (A_Turn <> 2) THEN A_Turn := 1; END_IF;
IF A_Emergency THEN
    A_GrantA := FALSE; A_GrantB := FALSE; A_Busy := FALSE; A_LockedOut := TRUE;
ELSE
    IF A_Reset AND (NOT A_RequestA) AND (NOT A_RequestB) THEN
        A_LockedOut := FALSE;
    END_IF;
    IF NOT A_LockedOut THEN
        IF A_Done THEN
            IF A_Busy THEN
                IF A_GrantA THEN A_Turn := 2; ELSE A_Turn := 1; END_IF;
            END_IF;
            A_GrantA := FALSE; A_GrantB := FALSE; A_Busy := FALSE;
        ELSIF NOT A_Busy THEN
            IF A_RequestA AND A_RequestB THEN
                IF A_Turn = 1 THEN A_GrantA := TRUE; ELSE A_GrantB := TRUE; END_IF;
                A_Busy := TRUE;
            ELSIF A_RequestA THEN
                A_GrantA := TRUE; A_GrantB := FALSE; A_Busy := TRUE;
            ELSIF A_RequestB THEN
                A_GrantA := FALSE; A_GrantB := TRUE; A_Busy := TRUE;
            END_IF;
        END_IF;
    END_IF;
END_IF;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_GrantA THEN
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
