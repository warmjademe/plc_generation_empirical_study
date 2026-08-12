FUNCTION_BLOCK C07_B11_composite
VAR_INPUT
    A_Raw : INT;
    B_Temperature : REAL;
    B_LowThreshold : REAL;
    B_HighThreshold : REAL;
    B_Enable : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Engineering : REAL;
    A_UnderRange : BOOL;
    A_OverRange : BOOL;
    B_Heater : BOOL;
    B_ConfigError : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
