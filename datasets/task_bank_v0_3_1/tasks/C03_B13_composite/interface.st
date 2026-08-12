FUNCTION_BLOCK C03_B13_composite
VAR_INPUT
    A_Temperature : REAL;
    A_Setpoint : REAL;
    A_Enable : BOOL;
    A_SafetyTrip : BOOL;
    B_RunRequest : BOOL;
    B_Stop : BOOL;
    B_C1Clear : BOOL;
    B_C2Clear : BOOL;
    B_C3Clear : BOOL;
    B_C2Available : BOOL;
    B_C3Available : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Heat : BOOL;
    A_Cool : BOOL;
    B_C1Run : BOOL;
    B_C2Run : BOOL;
    B_C3Run : BOOL;
    B_Blocked : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
END_FUNCTION_BLOCK
