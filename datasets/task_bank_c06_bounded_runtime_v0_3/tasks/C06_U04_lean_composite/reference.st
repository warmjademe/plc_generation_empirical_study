FUNCTION_BLOCK C06_U04_lean_composite
VAR_INPUT
    A_GoodPart : BOOL;
    A_RejectPart : BOOL;
    A_Reset : BOOL;
    A_BatchTarget : INT;
    A_RejectLimit : INT;
    B_AutoMode : BOOL;
    B_AutoDemand : BOOL;
    B_ManualDemand : BOOL;
    B_SafetyOK : BOOL;
    B_Inhibit : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_GoodCount : INT;
    A_RejectCount : INT;
    A_BatchDone : BOOL;
    A_QualityFault : BOOL;
    B_Command : BOOL;
    B_Blocked : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PrevGood : BOOL := FALSE;
    A_PrevReject : BOOL := FALSE;
END_VAR

IF A_Reset THEN
    A_GoodCount := 0;
    A_RejectCount := 0;
    A_QualityFault := FALSE;
ELSE
    IF A_RejectPart AND (NOT A_PrevReject) THEN
        A_RejectCount := A_RejectCount + 1;
    ELSIF A_GoodPart AND (NOT A_PrevGood) THEN
        A_GoodCount := A_GoodCount + 1;
    END_IF;
    IF A_RejectCount >= A_RejectLimit THEN
        A_QualityFault := TRUE;
    END_IF;
END_IF;
A_BatchDone := (A_GoodCount + A_RejectCount) >= A_BatchTarget;
A_PrevGood := A_GoodPart;
A_PrevReject := A_RejectPart;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_BatchDone THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

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
