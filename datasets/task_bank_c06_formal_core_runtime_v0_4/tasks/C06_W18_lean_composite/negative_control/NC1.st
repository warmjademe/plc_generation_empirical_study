FUNCTION_BLOCK C06_W18_lean_composite
VAR_INPUT
    A_AutoMode : BOOL;
    A_AutoDemand : BOOL;
    A_ManualDemand : BOOL;
    A_SafetyOK : BOOL;
    A_Inhibit : BOOL;
    B_Item : BOOL;
    B_Reset : BOOL;
    B_Target : INT;
    B_Enable : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Command : BOOL;
    A_Blocked : BOOL;
    B_Count : INT;
    B_BatchDone : BOOL;
    B_Accepted : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    B_PrevItem : BOOL := FALSE;
END_VAR

A_Command := ((A_AutoMode AND A_AutoDemand) OR ((NOT A_AutoMode) AND A_ManualDemand))
           AND A_SafetyOK AND (NOT A_Inhibit);
A_Blocked := ((A_AutoMode AND A_AutoDemand) OR ((NOT A_AutoMode) AND A_ManualDemand))
           AND ((NOT A_SafetyOK) OR A_Inhibit);

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Command THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := FALSE;

IF SubsystemBEnable AND CrossReady THEN
    B_Accepted := FALSE;
    IF B_Reset THEN
        B_Count := 0;
    ELSIF B_Enable AND B_Item AND (NOT B_PrevItem) AND (B_Count < B_Target) THEN
        B_Count := B_Count + 1;
        B_Accepted := TRUE;
    END_IF;
    B_BatchDone := B_Count >= B_Target;
    B_PrevItem := B_Item;
ELSE
    B_Count := 0;
    B_BatchDone := FALSE;
    B_Accepted := FALSE;
END_IF;

END_FUNCTION_BLOCK
