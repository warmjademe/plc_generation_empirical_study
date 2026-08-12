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

A_Heat := FALSE;
A_Cool := FALSE;
IF A_Enable AND (NOT A_SafetyTrip) THEN
    IF A_Temperature < (A_Setpoint - 1.0) THEN
        A_Heat := FALSE;
    ELSIF A_Temperature > (A_Setpoint + 1.0) THEN
        A_Cool := TRUE;
    END_IF;
END_IF;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Heat THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

IF SubsystemBEnable AND CrossReady THEN
    B_C3Run := B_RunRequest AND B_C3Available AND B_C3Clear AND (NOT B_Stop);
    B_C2Run := B_C3Run AND B_C2Available AND B_C2Clear;
    B_C1Run := B_C2Run AND B_C1Clear;
    B_Blocked := B_RunRequest AND ((NOT B_C1Clear) OR (NOT B_C2Clear) OR (NOT B_C3Clear)
               OR (NOT B_C2Available) OR (NOT B_C3Available));
ELSE
    B_C1Run := FALSE;
    B_C2Run := FALSE;
    B_C3Run := FALSE;
    B_Blocked := FALSE;
END_IF;

END_FUNCTION_BLOCK
