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
END_FUNCTION_BLOCK
