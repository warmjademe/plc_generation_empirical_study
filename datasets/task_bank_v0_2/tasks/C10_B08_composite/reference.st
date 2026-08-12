FUNCTION_BLOCK C10_B08_composite
VAR_INPUT
    A_RequestA : BOOL;
    A_RequestB : BOOL;
    A_Done : BOOL;
    A_Emergency : BOOL;
    A_Reset : BOOL;
    B_LowDemand : BOOL;
    B_HighDemand : BOOL;
    B_Lead : INT;
    B_Available1 : BOOL;
    B_Available2 : BOOL;
    B_Available3 : BOOL;
    B_Feedback1 : BOOL;
    B_Feedback2 : BOOL;
    B_Feedback3 : BOOL;
    B_Stop : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_GrantA : BOOL;
    A_GrantB : BOOL;
    A_Busy : BOOL;
    A_Turn : INT;
    A_LockedOut : BOOL;
    B_Run1 : BOOL;
    B_Run2 : BOOL;
    B_Run3 : BOOL;
    B_ActiveCount : INT;
    B_Failover : BOOL;
    B_Fault : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    B_NoFeedback1 : TON;
    B_NoFeedback2 : TON;
    B_NoFeedback3 : TON;
    B_Failed1 : BOOL;
    B_Failed2 : BOOL;
    B_Failed3 : BOOL;
    B_Valid1 : BOOL;
    B_Valid2 : BOOL;
    B_Valid3 : BOOL;
    B_RequiredCount : INT;
END_VAR

IF (A_Turn <> 1) AND (A_Turn <> 2) THEN A_Turn := 1; END_IF;
IF A_Emergency THEN
    A_GrantA := FALSE; A_GrantB := FALSE; A_Busy := FALSE; A_LockedOut := TRUE;
ELSIF A_Reset AND (NOT A_RequestA) AND (NOT A_RequestB) THEN
    A_LockedOut := FALSE;
ELSIF NOT A_LockedOut THEN
    IF A_Done AND A_Busy THEN
        IF A_GrantA THEN A_Turn := 2; ELSE A_Turn := 1; END_IF;
        A_GrantA := FALSE; A_GrantB := FALSE; A_Busy := FALSE;
    ELSIF NOT A_Busy THEN
        IF A_RequestA AND A_RequestB THEN
            IF A_Turn = 1 THEN A_GrantA := TRUE; ELSE A_GrantB := TRUE; END_IF;
            A_Busy := TRUE;
        ELSIF A_RequestA THEN
            A_GrantA := TRUE; A_GrantB := FALSE; A_Busy := TRUE;
        ELSIF A_RequestB THEN
            A_GrantA := FALSE; A_GrantB := TRUE; A_Busy := TRUE;
        END_IF;
    END_IF;
END_IF;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_GrantA THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

IF SubsystemBEnable AND CrossReady THEN
    B_NoFeedback1(IN := B_Run1 AND (NOT B_Feedback1), PT := T#300ms);
    B_NoFeedback2(IN := B_Run2 AND (NOT B_Feedback2), PT := T#300ms);
    B_NoFeedback3(IN := B_Run3 AND (NOT B_Feedback3), PT := T#300ms);
    IF B_NoFeedback1.Q THEN B_Failed1 := TRUE; END_IF;
    IF B_NoFeedback2.Q THEN B_Failed2 := TRUE; END_IF;
    IF B_NoFeedback3.Q THEN B_Failed3 := TRUE; END_IF;
    IF B_Reset AND (NOT B_LowDemand) AND (NOT B_HighDemand) AND (NOT B_Stop) THEN
        B_Failed1 := FALSE; B_Failed2 := FALSE; B_Failed3 := FALSE; B_Fault := FALSE;
    END_IF;
    B_Run1 := FALSE; B_Run2 := FALSE; B_Run3 := FALSE;
    B_RequiredCount := 0;
    IF B_HighDemand THEN B_RequiredCount := 2;
    ELSIF B_LowDemand THEN B_RequiredCount := 1;
    END_IF;
    B_Valid1 := B_Available1 AND (NOT B_Failed1);
    B_Valid2 := B_Available2 AND (NOT B_Failed2);
    B_Valid3 := B_Available3 AND (NOT B_Failed3);
    IF (NOT B_Stop) AND (B_RequiredCount > 0) THEN
        IF B_Lead = 2 THEN
            IF B_Valid2 THEN B_Run2 := TRUE;
            ELSIF B_Valid3 THEN B_Run3 := TRUE;
            ELSIF B_Valid1 THEN B_Run1 := TRUE;
            END_IF;
            IF B_RequiredCount = 2 THEN
                IF B_Valid3 AND (NOT B_Run3) THEN B_Run3 := TRUE;
                ELSIF B_Valid1 AND (NOT B_Run1) THEN B_Run1 := TRUE;
                ELSIF B_Valid2 AND (NOT B_Run2) THEN B_Run2 := TRUE;
                END_IF;
            END_IF;
        ELSIF B_Lead = 3 THEN
            IF B_Valid3 THEN B_Run3 := TRUE;
            ELSIF B_Valid1 THEN B_Run1 := TRUE;
            ELSIF B_Valid2 THEN B_Run2 := TRUE;
            END_IF;
            IF B_RequiredCount = 2 THEN
                IF B_Valid1 AND (NOT B_Run1) THEN B_Run1 := TRUE;
                ELSIF B_Valid2 AND (NOT B_Run2) THEN B_Run2 := TRUE;
                ELSIF B_Valid3 AND (NOT B_Run3) THEN B_Run3 := TRUE;
                END_IF;
            END_IF;
        ELSE
            IF B_Valid1 THEN B_Run1 := TRUE;
            ELSIF B_Valid2 THEN B_Run2 := TRUE;
            ELSIF B_Valid3 THEN B_Run3 := TRUE;
            END_IF;
            IF B_RequiredCount = 2 THEN
                IF B_Valid2 AND (NOT B_Run2) THEN B_Run2 := TRUE;
                ELSIF B_Valid3 AND (NOT B_Run3) THEN B_Run3 := TRUE;
                ELSIF B_Valid1 AND (NOT B_Run1) THEN B_Run1 := TRUE;
                END_IF;
            END_IF;
        END_IF;
    END_IF;
    B_ActiveCount := 0;
    IF B_Run1 THEN B_ActiveCount := B_ActiveCount + 1; END_IF;
    IF B_Run2 THEN B_ActiveCount := B_ActiveCount + 1; END_IF;
    IF B_Run3 THEN B_ActiveCount := B_ActiveCount + 1; END_IF;
    B_Failover := (B_RequiredCount > 0) AND ((B_ActiveCount < B_RequiredCount) OR ((B_Lead = 1) AND (NOT B_Run1)) OR ((B_Lead = 2) AND (NOT B_Run2)) OR ((B_Lead = 3) AND (NOT B_Run3)));
    IF B_ActiveCount < B_RequiredCount THEN B_Fault := TRUE; END_IF;
ELSE
    B_Run1 := FALSE;
    B_Run2 := FALSE;
    B_Run3 := FALSE;
    B_ActiveCount := 0;
    B_Failover := FALSE;
    B_Fault := FALSE;
END_IF;

END_FUNCTION_BLOCK
