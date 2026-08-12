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
END_FUNCTION_BLOCK
