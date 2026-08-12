FUNCTION_BLOCK C03_B03_composite
VAR_INPUT
    A_RunRequest : BOOL;
    A_Stop : BOOL;
    A_C1Clear : BOOL;
    A_C2Clear : BOOL;
    A_C3Clear : BOOL;
    A_C2Available : BOOL;
    A_C3Available : BOOL;
    B_Temperature : REAL;
    B_Setpoint : REAL;
    B_Enable : BOOL;
    B_SafetyTrip : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_C1Run : BOOL;
    A_C2Run : BOOL;
    A_C3Run : BOOL;
    A_Blocked : BOOL;
    B_Heat : BOOL;
    B_Cool : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR

A_C3Run := A_RunRequest AND A_C3Available AND A_C3Clear AND (NOT A_Stop);
A_C2Run := A_C3Run AND A_C2Available AND A_C2Clear;
A_C1Run := A_C2Run AND A_C1Clear;
A_Blocked := A_RunRequest AND ((NOT A_C1Clear) OR (NOT A_C2Clear) OR (NOT A_C3Clear)
           OR (NOT A_C2Available) OR (NOT A_C3Available));

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_C1Run THEN
    CrossReady := FALSE;
END_IF;
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

IF SubsystemBEnable AND CrossReady THEN
    B_Heat := FALSE;
    B_Cool := FALSE;
    IF B_Enable AND (NOT B_SafetyTrip) THEN
        IF B_Temperature < (B_Setpoint - 1.0) THEN
            B_Heat := TRUE;
        ELSIF B_Temperature > (B_Setpoint + 1.0) THEN
            B_Cool := TRUE;
        END_IF;
    END_IF;
ELSE
    B_Heat := FALSE;
    B_Cool := FALSE;
END_IF;

END_FUNCTION_BLOCK
