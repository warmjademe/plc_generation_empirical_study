FUNCTION_BLOCK C01_B11_composite
VAR_INPUT
    A_S1 : BOOL;
    A_S2 : BOOL;
    A_S3 : BOOL;
    B_AutoMode : BOOL;
    B_AutoDemand : BOOL;
    B_ManualDemand : BOOL;
    B_SafetyOK : BOOL;
    B_Inhibit : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Vote : BOOL;
    A_Unanimous : BOOL;
    B_Command : BOOL;
    B_Blocked : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR

A_Vote := (A_S1 AND A_S2) OR (A_S1 AND A_S3) OR (A_S2 AND A_S3);
A_Unanimous := (A_S1 AND A_S2 AND A_S3) OR ((NOT A_S1) AND (NOT A_S2) AND (NOT A_S3));

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Vote THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := FALSE;

IF SubsystemBEnable AND CrossReady THEN
    B_Command := ((B_AutoMode AND B_AutoDemand) OR ((NOT B_AutoMode) AND B_ManualDemand))
               AND B_SafetyOK AND (NOT B_Inhibit);
    B_Blocked := ((B_AutoMode AND B_AutoDemand) OR ((NOT B_AutoMode) AND B_ManualDemand))
               AND ((NOT B_SafetyOK) OR B_Inhibit);
ELSE
    B_Command := FALSE;
    B_Blocked := FALSE;
END_IF;

END_FUNCTION_BLOCK
