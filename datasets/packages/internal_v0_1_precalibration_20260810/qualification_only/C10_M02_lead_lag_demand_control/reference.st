FUNCTION_BLOCK C10_M02_lead_lag_demand_control
VAR_INPUT
    LowDemand : BOOL;
    HighDemand : BOOL;
    LeadIsPump1 : BOOL;
    Pump1Available : BOOL;
    Pump2Available : BOOL;
END_VAR
VAR_OUTPUT
    Pump1Run : BOOL;
    Pump2Run : BOOL;
    CapacityShortfall : BOOL;
END_VAR

Pump1Run := FALSE;
Pump2Run := FALSE;
IF HighDemand THEN
    Pump1Run := Pump1Available;
    Pump2Run := Pump2Available;
ELSIF LowDemand THEN
    IF LeadIsPump1 THEN
        IF Pump1Available THEN Pump1Run := TRUE;
        ELSIF Pump2Available THEN Pump2Run := TRUE;
        END_IF;
    ELSE
        IF Pump2Available THEN Pump2Run := TRUE;
        ELSIF Pump1Available THEN Pump1Run := TRUE;
        END_IF;
    END_IF;
END_IF;
CapacityShortfall := (HighDemand AND ((NOT Pump1Available) OR (NOT Pump2Available))) OR
    (LowDemand AND (NOT HighDemand) AND (NOT Pump1Available) AND (NOT Pump2Available));

END_FUNCTION_BLOCK
