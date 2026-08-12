FUNCTION_BLOCK C07_B06_composite
VAR_INPUT
    A_Value : REAL;
    A_Enable : BOOL;
    A_MaxRise : REAL;
    A_MaxFall : REAL;
    A_Reset : BOOL;
    B_Raw : INT;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Delta : REAL;
    A_Trip : BOOL;
    A_Ready : BOOL;
    B_Engineering : REAL;
    B_UnderRange : BOOL;
    B_OverRange : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
