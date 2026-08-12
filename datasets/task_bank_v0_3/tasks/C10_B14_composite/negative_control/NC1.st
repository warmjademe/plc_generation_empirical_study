FUNCTION_BLOCK C10_B14_composite
VAR_INPUT
    A_LowDemand : BOOL;
    A_HighDemand : BOOL;
    A_LeadIsPump1 : BOOL;
    A_Pump1Available : BOOL;
    A_Pump2Available : BOOL;
    B_RequestA : BOOL;
    B_RequestB : BOOL;
    B_Done : BOOL;
    B_Emergency : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Pump1Run : BOOL;
    A_Pump2Run : BOOL;
    A_CapacityShortfall : BOOL;
    B_GrantA : BOOL;
    B_GrantB : BOOL;
    B_Busy : BOOL;
    B_Turn : INT;
    B_LockedOut : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
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
    IF (B_Turn <> 1) AND (B_Turn <> 2) THEN B_Turn := 1; END_IF;
    IF B_Emergency THEN
        B_GrantA := FALSE; B_GrantB := FALSE; B_Busy := FALSE; B_LockedOut := TRUE;
    ELSE
        IF B_Reset AND (NOT B_RequestA) AND (NOT B_RequestB) THEN
            B_LockedOut := FALSE;
        END_IF;
        IF NOT B_LockedOut THEN
            IF B_Done THEN
                IF B_Busy THEN
                    IF B_GrantA THEN B_Turn := 2; ELSE B_Turn := 1; END_IF;
                END_IF;
                B_GrantA := FALSE; B_GrantB := FALSE; B_Busy := FALSE;
            ELSIF NOT B_Busy THEN
                IF B_RequestA AND B_RequestB THEN
                    IF B_Turn = 1 THEN B_GrantA := TRUE; ELSE B_GrantB := TRUE; END_IF;
                    B_Busy := TRUE;
                ELSIF B_RequestA THEN
                    B_GrantA := TRUE; B_GrantB := FALSE; B_Busy := TRUE;
                ELSIF B_RequestB THEN
                    B_GrantA := FALSE; B_GrantB := TRUE; B_Busy := TRUE;
                END_IF;
            END_IF;
        END_IF;
    END_IF;
ELSE
    B_GrantA := FALSE;
    B_GrantB := FALSE;
    B_Busy := FALSE;
    B_Turn := 0;
    B_LockedOut := FALSE;
END_IF;

END_FUNCTION_BLOCK
